"""Explicit reindex/retry without changing document identity or touching legacy FAISS."""
import hashlib
import json
from sqlalchemy.orm import Session
from models import Chunk, Document
from services.chunking_service import chunk_document
from services.document_loader import load_document
from services.ingestion import storage_path
from services.vector_store import get_backend, point_id
from services.errors import indexing_error_message


def reindex(document: Document, db: Session) -> Document:
    path = storage_path(document)
    extracted = load_document(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if document.status == "ready" and document.content_hash == digest:
        return document
    # Queries stop seeing the old version before any vector mutation starts.
    document.status, document.error_message = "processing", None
    db.commit()
    try:
        backend = get_backend()
        chunks = chunk_document(extracted, document.id, document.original_filename, document.owner_id)
        backend.delete(document.id, document.owner_id)
        backend.ingest(chunks)
        db.query(Chunk).filter_by(document_id=document.id, owner_id=document.owner_id).delete()
        db.add_all([Chunk(id=point_id(document.id, c.metadata["chunk_index"]), document_id=document.id,
                         owner_id=document.owner_id, text=c.page_content, metadata_json=json.dumps(c.metadata)) for c in chunks])
        document.page_count, document.chunk_count = extracted.page_count, len(chunks)
        document.content_hash, document.status = digest, "ready"
        document.summary = None
        db.commit()
    except Exception as exc:
        db.rollback()
        document.status = "failed"
        document.error_message = indexing_error_message(exc)
        db.commit()
        raise
    return document
