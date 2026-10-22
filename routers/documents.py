"""
routers/documents.py
----------------------
CRUD-style endpoints for managing previously uploaded documents:
listing, fetching, deleting, and generating a structured AI summary
(demonstrating the OpenAI Responses API's structured output feature).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Document, Chunk, User
from schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
)
from services.document_loader import load_document
from services.security import current_user, owned
from services.ingestion import storage_path
from services.errors import provider_error
from services.rag_service import generate_structured_summary
from services.vector_store import delete_document as delete_from_vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("", response_model=DocumentListResponse, summary="List all uploaded documents")
def list_documents(db: Session = Depends(get_db), user: User = Depends(current_user)) -> DocumentListResponse:
    documents = db.query(Document).filter(Document.owner_id == user.id).order_by(Document.created_at.desc()).all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d.to_dict()) for d in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get a single document")
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> DocumentResponse:
    document = owned(db, Document, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentResponse.model_validate(document.to_dict())


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and its vector index entries",
)
def delete_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    document = owned(db, Document, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    try:
        delete_from_vector_store(document_id, user.id)
    except Exception as exc:
        raise provider_error(exc) from exc
    removed_chunks = document.chunk_count

    file_path = storage_path(document)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError as exc:
            logger.warning("File cleanup failed document_id=%s", document_id)
            raise HTTPException(503, "Stored file could not be removed. Retry deletion after checking storage permissions.") from exc

    db.query(Chunk).filter_by(document_id=document_id, owner_id=user.id).delete()
    db.delete(document)
    db.commit()

    return {
        "deleted": True,
        "document_id": document_id,
        "removed_vector_chunks": removed_chunks,
    }


@router.post(
    "/{document_id}/summary",
    response_model=DocumentSummaryResponse,
    summary="Generate a structured AI summary (OpenAI Responses API + JSON Schema)",
)
def summarize_document(
    document_id: str,
    payload: DocumentSummaryRequest,
    db: Session = Depends(get_db), user: User = Depends(current_user),
) -> DocumentSummaryResponse:
    """
    Demonstrates the raw OpenAI Responses API with structured output:
    the model is constrained to return JSON matching a fixed schema
    (title, overview, key_points, document_type, estimated reading
    time), which we validate and cache on the document record.
    """
    document = owned(db, Document, document_id, user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not ready for summarization (status: {document.status}).",
        )

    file_path = storage_path(document)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The original PDF file is no longer available on disk.",
        )

    try:
        extracted = load_document(file_path)
        summary_dict = generate_structured_summary(
            extracted.full_text, max_key_points=payload.max_key_points
        )
        summary_dict = DocumentSummaryResponse.model_validate(summary_dict).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Summary failed document_id=%s error_type=%s", document_id, type(exc).__name__)
        raise provider_error(exc) from exc

    import json

    document.summary = json.dumps(summary_dict)
    db.commit()

    return DocumentSummaryResponse.model_validate(summary_dict)


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = owned(db, Document, document_id, user.id)
    path = storage_path(document)
    if not path.is_file():
        raise HTTPException(410, "Original document is no longer available.")
    return FileResponse(path, filename=document.original_filename, media_type="application/octet-stream")


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
def reindex_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    from services.document_updates import reindex
    from services.pdf_loader import PDFExtractionError
    document = owned(db, Document, document_id, user.id)
    try:
        return DocumentResponse.model_validate(reindex(document, db).to_dict())
    except PDFExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise provider_error(exc) from exc
