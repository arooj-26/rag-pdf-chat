"""Expose only the checked-in safe fixture report, never private evaluation input."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from models import User
from services.security import current_user

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


@router.get("")
def evaluation_report(user: User = Depends(current_user)):
    path = Path(__file__).resolve().parent.parent / "docs" / "evaluation_report.json"
    if not path.is_file():
        raise HTTPException(404, "Run python -m evaluation.run to generate the fixture report.")
    return json.loads(path.read_text(encoding="utf-8"))
