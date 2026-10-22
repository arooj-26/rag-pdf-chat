"""Authenticated multi-format upload API."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import DocumentListResponse, DocumentResponse
from services.security import current_user
from services.ingestion import ingest

router = APIRouter(prefix="/api/upload", tags=["Upload"])

@router.post("", response_model=DocumentListResponse, status_code=201)
def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not 1 <= len(files) <= 10:
        raise HTTPException(400, "Upload between one and ten files per request.")
    documents = [ingest(file, db, user.id) for file in files]
    return DocumentListResponse(documents=[DocumentResponse.model_validate(d.to_dict()) for d in documents], total=len(documents))
