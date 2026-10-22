"""BM25 and Reciprocal Rank Fusion over a SQL-authorized, ready-only corpus."""
import json
import re
from langchain_core.documents import Document as LCDocument
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from config import get_settings
from models import Chunk, Document
from services.security import owned
from services.vector_store import get_backend


def tokens(text: str) -> list[str]:
    return re.findall(r"[\w-]+", text.lower())


def keyword_search(query: str, docs: list[LCDocument], k: int) -> list[LCDocument]:
    if not docs or not tokens(query):
        return []
    corpus = [tokens(d.page_content) or [""] for d in docs]
    scores = BM25Okapi(corpus).get_scores(tokens(query))
    # Some tiny corpora produce zero/negative IDF. Retain exact token matches.
    matches = [i for i, words in enumerate(corpus) if set(tokens(query)) & set(words)]
    return [docs[i] for i in sorted(matches, key=lambda i: (-scores[i], i))[:k]]


def fuse(rankings: list[list[LCDocument]], k: int, constant: int = 60) -> list[LCDocument]:
    scores, documents = {}, {}
    for ranking in rankings:
        seen = set()
        for rank, doc in enumerate(ranking, 1):
            identity = doc.metadata["chunk_id"]
            if identity in seen:
                continue
            seen.add(identity)
            documents[identity] = doc
            scores[identity] = scores.get(identity, 0) + 1 / (constant + rank)
    return [documents[i] for i in sorted(scores, key=lambda i: (-scores[i], i))[:k]]


def retrieve(db: Session, owner_id: str, query: str, document_ids: list[str] | None = None,
             mode: str | None = None, k: int | None = None, *, backend=None) -> list[LCDocument]:
    settings = get_settings()
    mode, k = mode or settings.retrieval_mode, k or settings.retriever_k
    if mode not in {"semantic", "keyword", "hybrid"}:
        raise ValueError("Unsupported retrieval mode")
    if not owner_id:
        raise ValueError("An authenticated owner is required")
    if document_ids is not None:
        for doc_id in document_ids:
            owned(db, Document, doc_id, owner_id)
    authorized = db.query(Document.id).filter(Document.owner_id == owner_id, Document.status == "ready")
    if document_ids is not None:
        authorized = authorized.filter(Document.id.in_(document_ids))
    ids = [r[0] for r in authorized.all()]
    if not ids:
        return []
    rows = db.query(Chunk).filter(Chunk.owner_id == owner_id, Chunk.document_id.in_(ids)).all()
    docs = [LCDocument(page_content=c.text, metadata=json.loads(c.metadata_json)) for c in rows]
    limit = settings.retrieval_candidates
    dense = (backend or get_backend()).search(query, owner_id, ids, limit) if mode != "keyword" else []
    # Defense in depth: SQL chunks are the source of truth, including deletion state.
    valid = {d.metadata["chunk_id"]: d for d in docs}
    dense = [valid[d.metadata["chunk_id"]] for d in dense if d.metadata.get("chunk_id") in valid]
    sparse = keyword_search(query, docs, limit) if mode != "semantic" else []
    ranked = fuse([dense, sparse], limit, settings.rrf_constant) if mode == "hybrid" else (dense if mode == "semantic" else sparse)
    if settings.rerank_enabled:
        # Lightweight lexical reranker, no extra external model or document transmission.
        q = set(tokens(query))
        ranked.sort(key=lambda d: -len(q & set(tokens(d.page_content))))
    return ranked[:k]
