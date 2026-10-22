import json
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from main import app
from tests.conftest import account
from tests.test_security_rag import upload
from tests.test_migration_ocr import text_pdf
from services.rag_service import docs_to_source_dicts, format_docs_for_context
from langchain_core.documents import Document


def test_download_boundaries(signed_client):
    doc_id = upload(signed_client)
    response = signed_client.get(f"/api/documents/{doc_id}/download")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    with TestClient(app) as bob:
        account(bob, "bob@example.com")
        assert bob.get(f"/api/documents/{doc_id}/download").status_code == 403


def test_all_format_ingestion(signed_client, tmp_path):
    from docx import Document as Word
    path = tmp_path / "biology.pdf"; text_pdf(path)
    doc = Word(); doc.add_paragraph("Mitochondria generate ATP."); doc.save(tmp_path / "biology.docx")
    files = [("files", ("biology.pdf", path.read_bytes(), "application/pdf")),
             ("files", ("biology.docx", (tmp_path / "biology.docx").read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
             ("files", ("biology.md", b"# Cell biology\nMitochondria generate ATP.", "text/markdown"))]
    response = signed_client.post("/api/upload", files=files)
    assert response.status_code == 201, response.text
    assert all(d["status"] == "ready" for d in response.json()["documents"])
    results = signed_client.post("/api/search", json={"query": "Mitochondria", "mode": "keyword", "k": 20}).json()["sources"]
    assert {s["source_type"] for s in results} == {"pdf", "docx", "md"}
    assert next(s for s in results if s["source_type"] == "pdf")["page"] == 1


def test_chat_citations(signed_client, monkeypatch):
    from services import rag_service
    from langchain_core.runnables import RunnableLambda
    doc_id = upload(signed_client)
    monkeypatch.setattr(rag_service, "_get_chat_llm", lambda **kw: RunnableLambda(lambda prompt: "Mitochondria generate ATP [Source 1]."))
    response = signed_client.post("/api/chat", json={"document_id": doc_id, "message": "What generates ATP?"})
    assert response.status_code == 200, response.text
    assert response.json()["sources"][0]["document_id"] == doc_id
    assert "Source 1" in response.json()["message"]["content"]


def test_stream_citations(signed_client, monkeypatch):
    from services import rag_service
    from langchain_core.runnables import RunnableLambda
    doc_id = upload(signed_client)
    monkeypatch.setattr(rag_service, "_get_chat_llm", lambda **kw: RunnableLambda(lambda prompt: "ATP [Source 1]."))
    response = signed_client.post("/api/chat/stream", json={"document_id": doc_id, "message": "ATP?"})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert any(e["type"] == "sources" and e["sources"][0]["document_id"] == doc_id for e in events)
    assert any(e["type"] == "token" for e in events)
    assert events[-1]["type"] == "close"


def test_provider_error_no_secrets(signed_client, monkeypatch):
    from routers import chat
    def error(*a, **kw): raise RuntimeError("sk-secret private content")
    monkeypatch.setattr(chat, "generate_answer", error)
    response = signed_client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 503
    assert "sk-secret" not in response.text


def test_summary_validation(signed_client, monkeypatch):
    from routers import documents
    doc_id = upload(signed_client)
    summary = {"title": "Biology", "overview": "ATP production", "key_points": ["Mitochondria generate ATP"], "document_type": "notes", "estimated_reading_time_minutes": 1}
    monkeypatch.setattr(documents, "generate_structured_summary", lambda *a, **kw: summary)
    response = signed_client.post(f"/api/documents/{doc_id}/summary", json={})
    assert response.status_code == 200
    assert response.json()["title"] == "Biology"


def test_rate_limit(signed_client, monkeypatch):
    from config import get_settings
    from services.request_guard import _buckets
    _buckets.clear()
    monkeypatch.setattr(get_settings(), "requests_per_minute", 2)
    assert signed_client.get("/api/documents").status_code == 200
    assert signed_client.get("/api/documents").status_code == 200
    response = signed_client.get("/api/documents")
    assert response.status_code == 429
    assert response.headers["Retry-After"]


def test_upload_limit(signed_client, monkeypatch):
    from config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)
    response = signed_client.post("/api/upload", files={"files": ("large.txt", b"a" * (1024 * 1024 + 1), "text/plain")})
    assert response.status_code == 413


def test_no_invented_page():
    docs = [Document(page_content="Information", metadata={"document_id": "d", "document_name": "notes.md", "chunk_id": "d:0", "chunk_index": 0, "page": None, "section": "Intro"})]
    assert "page" not in format_docs_for_context(docs)
    assert "section Intro" in format_docs_for_context(docs)
    assert docs_to_source_dicts(docs)[0]["page"] is None


def test_reindex_unchanged_and_updated(signed_client, setup_app):
    from pathlib import Path
    from models import Document
    doc_id = upload(signed_client)
    factory, backend = setup_app
    before = backend.client.count("test").count
    assert signed_client.post(f"/api/documents/{doc_id}/reindex").status_code == 200
    assert backend.client.count("test").count == before
    with factory() as db:
        path = Path(db.get(Document, doc_id).file_path)
        path.write_text("New study content: chloroplasts perform photosynthesis.", encoding="utf-8")
    assert signed_client.post(f"/api/documents/{doc_id}/reindex").status_code == 200
    sources = signed_client.post("/api/search", json={"query": "photosynthesis", "mode": "keyword"}).json()["sources"]
    assert sources[0]["document_id"] == doc_id
    assert "photosynthesis" in sources[0]["text_snippet"]


def test_reindex_owner_boundary(signed_client):
    doc_id = upload(signed_client)
    with TestClient(app) as bob:
        account(bob, "bob@example.com")
        assert bob.post(f"/api/documents/{doc_id}/reindex").status_code == 403
