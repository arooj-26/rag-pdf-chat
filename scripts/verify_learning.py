"""Generate study material through the running local API for one stored document.

Requires local DB access. A temporary, short-lived session is removed on completion.
Uses the configured AI provider and saves successful material to the document owner.
Does not print authentication credentials, document text or generated answers.
"""
import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id")
    parser.add_argument("--kind", choices=["flashcards", "quiz", "notes"], default="flashcards")
    parser.add_argument("--count", type=int, default=5, choices=range(1, 21))
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ["DEBUG"] = "false"
    import httpx
    from database import SessionLocal
    from models import Document, UserSession
    from services.security import COOKIE_NAME, signer, token_hash
    token, csrf = secrets.token_urlsafe(32), secrets.token_hex(32)
    hashed = token_hash(token)
    with SessionLocal() as db:
        document = db.get(Document, args.document_id)
        if document is None or document.status != "ready" or not document.owner_id:
            print("Choose an owned, ready document.")
            return 1
        db.add(UserSession(token_hash=hashed, user_id=document.owner_id, csrf_token=csrf,
                           expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)))
        db.commit()
    try:
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=180,
                          cookies={COOKIE_NAME: signer().dumps(token)},
                          headers={"X-CSRF-Token": csrf}) as client:
            response = client.post(f"/api/learning/generate/{args.kind}", json={"document_ids": [args.document_id], "count": args.count})
            print("API response status:", response.status_code)
            if response.status_code != 201:
                detail = response.json().get("detail", "Generation failed.")
                print("API error:", detail if isinstance(detail, str) else "Input validation failed.")
                return 1
            result = response.json()
            key = {"flashcards": "cards", "quiz": "questions", "notes": "notes"}[args.kind]
            print("Saved material ID:", result["id"])
            print("Generated item count:", len(result["content"][key]))
            print("Source reference count:", len(result["sources"]))
            return 0
    except Exception as exc:
        print("Local API check failed; error type:", type(exc).__name__)
        return 1
    finally:
        with SessionLocal() as db:
            db.query(UserSession).filter_by(token_hash=hashed).delete()
            db.commit()


if __name__ == "__main__":
    raise SystemExit(main())
