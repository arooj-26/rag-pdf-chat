"""Authentication endpoints. No credential or session token enters localStorage."""
import re
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db
from models import User, UserSession
from services.security import COOKIE_NAME, current_session, owned, signer, token_hash

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
hasher = PasswordHasher()
dummy_hash = hasher.hash("dummy-password-for-timing-only")


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value


def check_origin(request: Request) -> None:
    # Auth bootstrap has no session CSRF token yet: require a non-simple JSON request
    # and same-origin browser fetch metadata. CORS allows no origins by default.
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site authentication request rejected.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-site authentication request rejected.")


def establish(user: User, response: Response, db: Session) -> dict:
    settings = get_settings()
    token, csrf = secrets.token_urlsafe(32), secrets.token_hex(32)
    db.add(UserSession(token_hash=token_hash(token), user_id=user.id, csrf_token=csrf,
                       expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=settings.session_hours)))
    db.commit()
    response.set_cookie(COOKIE_NAME, signer().dumps(token), httponly=True,
                        secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours * 3600)
    response.headers["Cache-Control"] = "no-store"
    return {"id": user.id, "email": user.email, "csrf_token": csrf}


@router.post("/register", status_code=201)
def register(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    user = User(email=payload.email, password_hash=hasher.hash(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists.")
    return establish(user, response, db)


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    user = db.query(User).filter_by(email=payload.email).first()
    try:
        hasher.verify(user.password_hash if user else dummy_hash, payload.password)
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, "Invalid email or password.")
    if user is None:
        raise HTTPException(401, "Invalid email or password.")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(payload.password)
    return establish(user, response, db)


@router.get("/me")
def me(response: Response, session: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    response.headers["Cache-Control"] = "no-store"
    return {"id": user.id, "email": user.email, "csrf_token": session.csrf_token}


@router.post("/logout")
def logout(response: Response, session: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"logged_out": True}
