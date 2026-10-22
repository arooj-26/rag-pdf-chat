from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import User
from services.security import current_user
from services.hybrid_retrieval import retrieve
from services.rag_service import docs_to_source_dicts
from services.errors import provider_error

router = APIRouter(prefix="/api/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] | None = Field(default=None, max_length=50)
    mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    k: int = Field(default=4, ge=1, le=20)


@router.post("")
def search(payload: SearchRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from fastapi import HTTPException
    try:
        return {"sources": docs_to_source_dicts(retrieve(db, user.id, payload.query, payload.document_ids, payload.mode, payload.k))}
    except HTTPException:
        raise
    except Exception as exc:
        raise provider_error(exc) from exc
