from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import LearningArtifact, User
from services.security import current_user, owned
from services.learning_schemas import LearningRequest, QuizSubmission
from services.learning_service import generate, present, score
from services.errors import provider_error

router = APIRouter(prefix="/api/learning", tags=["Learning"])


@router.get("")
def list_artifacts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(LearningArtifact).filter_by(owner_id=user.id).order_by(LearningArtifact.created_at.desc()).limit(100).all()
    return [{"id": row.id, "kind": row.kind, "created_at": row.created_at.isoformat()} for row in rows]


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return present(owned(db, LearningArtifact, artifact_id, user.id))


@router.delete("/{artifact_id}")
def delete_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(owned(db, LearningArtifact, artifact_id, user.id))
    db.commit()
    return {"deleted": True}


@router.post("/generate/{kind}", status_code=201)
def generate_artifact(kind: str, payload: LearningRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return present(generate(kind, payload, db, user.id))
    except HTTPException:
        raise
    except (ValueError, TypeError) as exc:
        raise HTTPException(502, "AI output lacked valid supporting evidence. Try fewer items or a different topic.") from exc
    except Exception as exc:
        raise provider_error(exc) from exc


@router.post("/{artifact_id}/submit")
def submit_quiz(artifact_id: str, payload: QuizSubmission, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return score(owned(db, LearningArtifact, artifact_id, user.id), payload.answers)
