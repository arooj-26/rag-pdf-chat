"""Revocable signed cookie sessions and reusable backend ownership checks."""
import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db
from models import User, UserSession

COOKIE_NAME = "research_session"


def signer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="research-session-v1")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    try:
        token = signer().loads(request.cookies.get(COOKIE_NAME, ""))
        row = db.get(UserSession, token_hash(token))
    except (BadSignature, TypeError):
        row = None
    if row is None or row.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(401, "Please sign in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row.csrf_token):
            raise HTTPException(403, "Invalid CSRF token. Refresh the page.")
    return row


def current_user(session: UserSession = Depends(current_session), db: Session = Depends(get_db)) -> User:
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "Please sign in again.")
    return user


def owned(db: Session, model, resource_id: str, owner_id: str):
    row = db.get(model, resource_id)
    if row is None:
        raise HTTPException(404, "Resource not found.")
    if row.owner_id != owner_id:
        raise HTTPException(403, "You do not have permission to access this resource.")
    return row
