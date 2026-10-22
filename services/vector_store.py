"""Qdrant adapter. Every operation requires an explicit owner scope."""
from functools import lru_cache
from uuid import UUID, uuid5, NAMESPACE_URL
from typing import Protocol
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from config import get_settings
from services.embedding_service import get_embeddings
from services.errors import IndexingServiceError


class VectorStoreError(RuntimeError):
    pass


class VectorBackend(Protocol):
    def ingest(self, chunks: list[Document]) -> list[str]: ...
    def search(self, query: str, owner_id: str, document_ids: list[str], k: int) -> list[Document]: ...
    def delete(self, document_id: str, owner_id: str) -> None: ...


def point_id(document_id: str, index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"research:{document_id}:{index}"))


def scope_filter(owner_id: str, document_ids: list[str]) -> models.Filter:
    if not owner_id:
        raise ValueError("An authenticated owner is required")
    return models.Filter(must=[
        models.FieldCondition(key="metadata.owner_id", match=models.MatchValue(value=owner_id)),
        models.FieldCondition(key="metadata.document_id", match=models.MatchAny(any=document_ids)),
    ])


class QdrantBackend:
    def __init__(self, client, embeddings, collection: str, dimensions: int):
        self.client, self.embeddings = client, embeddings
        self.collection, self.dimensions = collection, dimensions

    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            try:
                self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE))
            except Exception:
                # Another worker may have created the collection; validate it below.
                if not self.client.collection_exists(self.collection):
                    raise
        config = self.client.get_collection(self.collection).config.params.vectors
        if not isinstance(config, models.VectorParams) or config.size != self.dimensions or config.distance != models.Distance.COSINE:
            raise VectorStoreError("Qdrant dimensions or distance mismatch; use a new collection and reindex.")

    def ingest(self, chunks: list[Document]) -> list[str]:
        if not chunks:
            return []
        if any(not d.metadata.get("owner_id") or not d.metadata.get("document_id") for d in chunks):
            raise ValueError("All chunks need owner and document metadata")
        # Finish embedding before any vector writes, avoiding partial embedding batches.
        try:
            vectors = self.embeddings.embed_documents([d.page_content for d in chunks])
        except Exception as exc:
            raise IndexingServiceError("embeddings", exc) from exc
        if len(vectors) != len(chunks) or any(len(v) != self.dimensions for v in vectors):
            raise VectorStoreError("Embedding dimensions do not match the collection.")
        try:
            self.ensure_collection()
            ids = [point_id(d.metadata["document_id"], d.metadata["chunk_index"]) for d in chunks]
            points = [models.PointStruct(id=i, vector=v, payload={"page_content": d.page_content, "metadata": d.metadata}) for i, v, d in zip(ids, vectors, chunks)]
            for start in range(0, len(points), 64):
                self.client.upsert(self.collection, points[start:start+64], wait=True)
        except Exception as exc:
            raise IndexingServiceError("qdrant", exc) from exc
        return ids

    def search(self, query: str, owner_id: str, document_ids: list[str], k: int) -> list[Document]:
        filters = scope_filter(owner_id, document_ids)
        if not document_ids:
            return []
        self.ensure_collection()
        vector = self.embeddings.embed_query(query)
        if len(vector) != self.dimensions:
            raise VectorStoreError("Query embedding dimensions mismatch.")
        store = QdrantVectorStore(client=self.client, collection_name=self.collection,
            embedding=self.embeddings, validate_embeddings=False, validate_collection_config=False)
        return store.similarity_search_by_vector(vector, k=k, filter=filters)

    def delete(self, document_id: str, owner_id: str) -> None:
        filters = scope_filter(owner_id, [document_id])
        if self.client.collection_exists(self.collection):
            self.client.delete(self.collection, models.FilterSelector(filter=filters), wait=True)


@lru_cache
def get_backend() -> QdrantBackend:
    settings = get_settings()
    embeddings = get_embeddings()
    try:
        client = QdrantClient(path=settings.qdrant_path) if settings.qdrant_path else QdrantClient(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=int(settings.request_timeout))
    except Exception as exc:
        raise IndexingServiceError("qdrant", exc) from exc
    return QdrantBackend(client, embeddings, settings.qdrant_collection, settings.embedding_dimensions)


def add_document_chunks(chunks: list[Document]) -> list[str]:
    return get_backend().ingest(chunks)


def delete_document(document_id: str, owner_id: str) -> None:
    get_backend().delete(document_id, owner_id)
