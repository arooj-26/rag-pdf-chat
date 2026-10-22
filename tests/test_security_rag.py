import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from main import app
from models import UserSession, Document, Chunk
from tests.conftest import account


def upload(client, text=b"Mitochondria generate ATP. The identifier is BIO-721."):
    response = client.post("/api/upload", files={"files": ("biology.txt", text, "text/plain")})
    assert response.status_code == 201, response.text
    assert response.json()["documents"][0]["status"] == "ready"
    return response.json()["documents"][0]["id"]


def test_auth_lifecycle(client, setup_app):
    assert client.get("/api/documents").status_code == 401
    user = account(client)
    cookie = client.cookies.get("research_session")
    assert client.get("/api/auth/me").json()["id"] == user["id"]
    assert client.post("/api/auth/logout").status_code == 200
    client.cookies.set("research_session", cookie)
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "a-long-safe-password"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "wrong-long-password"}).status_code == 401


def test_session_cookie_flags_and_duplicate_registration(client):
    response = client.post("/api/auth/register", json={"email": "alice@example.com", "password": "long-enough-password"})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.post("/api/auth/register", json={"email": "alice@example.com", "password": "long-enough-password"}).status_code == 409


def test_csrf(signed_client):
    signed_client.headers.pop("X-CSRF-Token")
    assert signed_client.post("/api/upload", files={"files": ("a.txt", b"test", "text/plain")}).status_code == 403
    assert signed_client.post("/api/auth/logout").status_code == 403


def test_validation_and_origin(client):
    assert client.post("/api/auth/register", json={"email": "invalid", "password": "short"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "x@y.com", "password": "long-enough-password"}, headers={"Origin": "https://evil.example"}).status_code == 403


def test_expiry(signed_client, setup_app):
    factory, _ = setup_app
    with factory() as db:
        db.query(UserSession).update({"expires_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)})
        db.commit()
    assert signed_client.get("/api/auth/me").status_code == 401


def test_boundaries(signed_client, setup_app):
    doc_id = upload(signed_client)
    conv = signed_client.post("/api/conversations", json={"document_id": doc_id}).json()["id"]
    with TestClient(app) as bob:
        account(bob, "bob@example.com")
        assert bob.get("/api/documents").json()["total"] == 0
        assert bob.get("/api/conversations").json()["total"] == 0
        for method, url, kwargs in [
            ("get", f"/api/documents/{doc_id}", {}),
            ("delete", f"/api/documents/{doc_id}", {}),
            ("post", f"/api/documents/{doc_id}/summary", {"json": {}}),
            ("get", f"/api/conversations/{conv}/messages", {}),
            ("delete", f"/api/conversations/{conv}", {}),
            ("post", "/api/conversations", {"json": {"document_id": doc_id}}),
            ("post", "/api/chat", {"json": {"conversation_id": conv, "message": "hello"}}),
            ("post", "/api/chat/stream", {"json": {"document_id": doc_id, "message": "hello"}}),
            ("post", "/api/search", {"json": {"document_ids": [doc_id], "query": "ATP"}}),
        ]:
            assert getattr(bob, method)(url, **kwargs).status_code == 403, url
        for mode in ["semantic", "keyword", "hybrid"]:
            assert bob.post("/api/search", json={"query": "ATP", "mode": mode}).json()["sources"] == []


@pytest.mark.parametrize("mode", ["semantic", "keyword", "hybrid"])
def test_search_delete(signed_client, setup_app, mode):
    doc_id = upload(signed_client)
    sources = signed_client.post("/api/search", json={"query": "BIO-721", "mode": mode}).json()["sources"]
    assert sources[0]["document_id"] == doc_id
    assert sources[0]["page"] is None
    assert sources[0]["chunk_id"]
    assert signed_client.delete(f"/api/documents/{doc_id}").status_code == 200
    factory, backend = setup_app
    assert backend.client.count("test").count == 0
    with factory() as db:
        assert db.query(Chunk).count() == 0


def test_deduplication(signed_client, setup_app):
    first, second = upload(signed_client), upload(signed_client)
    assert first == second
    assert signed_client.get("/api/documents").json()["total"] == 1


def test_partial_ingestion(signed_client, setup_app, monkeypatch):
    _, backend = setup_app
    real = backend.ingest
    def fail(chunks):
        real(chunks)
        raise RuntimeError("SECRET provider content")
    monkeypatch.setattr(backend, "ingest", fail)
    response = signed_client.post("/api/upload", files={"files": ("notes.txt", b"private content", "text/plain")})
    assert response.json()["documents"][0]["status"] == "failed"
    assert "SECRET" not in response.text
    assert signed_client.post("/api/search", json={"query": "private"}).json()["sources"] == []
    assert backend.client.count("test").count == 0


def test_stream_empty(signed_client):
    response = signed_client.post("/api/chat/stream", json={"message": "unsupported question"})
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["start", "sources", "token", "close"]
    conv = events[0]["conversation_id"]
    messages = signed_client.get(f"/api/conversations/{conv}/messages").json()
    assert len(messages) == 2


def test_bad_filename_and_content(signed_client):
    for name, content, status in [("../evil.txt", b"text", 400), ("x.exe", b"text", 415), ("x.txt", b"\x00binary", 422), ("x.pdf", b"fake", 422)]:
        response = signed_client.post("/api/upload", files={"files": (name, content, "text/plain")})
        assert response.status_code == status


def test_dimensions(setup_app):
    _, backend = setup_app
    backend.ensure_collection()
    backend.dimensions = 999
    with pytest.raises(RuntimeError, match="dimensions"):
        backend.ensure_collection()
