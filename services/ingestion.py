"""Ingestion state machine: SQL ready status gates visibility of all vector writes."""
import hashlib
import json
import logging
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from config import get_settings
from models import Chunk, Document
from services.chunking_service import chunk_document
from services.document_loader import LOADERS, load_document
from services.pdf_loader import PDFExtractionError
from services.vector_store import get_backend, point_id
from services.errors import IndexingServiceError, indexing_error_message

logger = logging.getLogger(__name__)


def storage_path(document: Document) -> Path:
    path, root = Path(document.file_path).resolve(), get_settings().upload_dir.resolve()
    if not path.is_relative_to(root):
        raise HTTPException(403, "Invalid document storage path.")
    return path


def ingest(file: UploadFile, db: Session, owner_id: str) -> Document:
    settings = get_settings()
    name = file.filename or ""
    if len(name) > 200 or "/" in name or "\\" in name or ":" in name or any(ord(c) < 32 for c in name):
        raise HTTPException(400, "Invalid filename.")
    suffix = Path(name).suffix.lower()
    if suffix not in LOADERS:
        raise HTTPException(415, "Supported formats: PDF, DOCX, TXT and Markdown.")
    doc_id = str(uuid4())
    path = settings.upload_dir / f"{doc_id}{suffix}"
    size, digest = 0, hashlib.sha256()
    try:
        with path.open("xb") as target:
            while data := file.file.read(1024 * 1024):
                size += len(data)
                if size > settings.max_upload_size_bytes:
                    raise HTTPException(413, "File exceeds the upload size limit.")
                target.write(data)
                digest.update(data)
        existing = db.query(Document).filter_by(owner_id=owner_id, content_hash=digest.hexdigest(), source_type=suffix[1:], status="ready").first()
        if existing:
            path.unlink()
            return existing
        extracted = load_document(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, PDFExtractionError):
            raise HTTPException(422, str(exc)) from exc
        raise
    document = Document(id=doc_id, owner_id=owner_id, filename=path.name, original_filename=name,
                        file_path=str(path), source_type=suffix[1:], content_hash=digest.hexdigest(),
                        file_size_bytes=size, status="processing")
    db.add(document)
    db.commit()
    try:
        chunks = chunk_document(extracted, doc_id, name, owner_id)
        get_backend().ingest(chunks)
        db.add_all([Chunk(id=point_id(doc_id, c.metadata["chunk_index"]), document_id=doc_id,
                         owner_id=owner_id, text=c.page_content, metadata_json=json.dumps(c.metadata)) for c in chunks])
        document.page_count, document.chunk_count = extracted.page_count, len(chunks)
        document.status = "ready"
        db.commit()
    except Exception as exc:
        stage = exc.stage if isinstance(exc, IndexingServiceError) else "indexing"
        original = exc.original if isinstance(exc, IndexingServiceError) else exc
        logger.warning("Ingestion failed document_id=%s stage=%s error_type=%s", doc_id, stage, type(original).__name__)
        db.rollback()
        document = db.get(Document, doc_id)
        document.status, document.error_message = "failed", indexing_error_message(exc)
        db.commit()
        try:
            get_backend().delete(doc_id, owner_id)
        except Exception:
            # Orphans stay invisible because every search filters SQL ready document IDs.
            logger.warning("Vector cleanup pending document_id=%s", doc_id)
    return document
