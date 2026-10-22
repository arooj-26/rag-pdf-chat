from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from main import app
from tests.conftest import account
from tests.test_security_rag import upload
from services.learning_schemas import QuizQuestion, Flashcards


def generated(kind, bad_evidence=False):
    evidence = {"source_number": 1, "quote": "Unsupported fabricated statement" if bad_evidence else "Mitochondria generate ATP."}
    if kind == "quiz":
        return {"title": "Biology", "questions": [{"question": "What do mitochondria generate?", "options": ["ATP", "DNA", "RNA", "Starch"], "correct_answer": 0, "explanation": "The document states that mitochondria generate ATP.", "evidence": evidence}]}
    if kind == "flashcards":
        return {"title": "Biology", "cards": [{"front": "Mitochondria produce?", "back": "ATP", "evidence": evidence}]}
    return {"title": "Biology", "notes": [{"concept": "Mitochondria", "definition": "ATP-generating structures", "explanation": "Mitochondria generate ATP.", "takeaway": "ATP production", "evidence": evidence}]}


@pytest.mark.parametrize("kind", ["quiz", "flashcards", "notes"])
def test_generation_owner_and_scoring(signed_client, monkeypatch, kind):
    from services import learning_service
    doc_id = upload(signed_client)
    model = Mock()
    model.with_structured_output.return_value.invoke.return_value = generated(kind)
    monkeypatch.setattr(learning_service, "_get_chat_llm", lambda **kw: model)
    response = signed_client.post(f"/api/learning/generate/{kind}", json={"document_ids": [doc_id], "count": 1})
    assert response.status_code == 201, response.text
    data = response.json()
    assert signed_client.get(f"/api/learning/{data['id']}").status_code == 200
    if kind == "quiz":
        assert "correct_answer" not in response.text
        assert "explanation" not in response.text
        result = signed_client.post(f"/api/learning/{data['id']}/submit", json={"answers": [0]})
        assert result.json()["score"] == 1
        assert signed_client.post(f"/api/learning/{data['id']}/submit", json={"answers": [4]}).status_code == 422
    with TestClient(app) as bob:
        account(bob, "bob@example.com")
        assert bob.get("/api/learning").json() == []
        assert bob.get(f"/api/learning/{data['id']}").status_code == 403
        assert bob.delete(f"/api/learning/{data['id']}").status_code == 403
        assert bob.post(f"/api/learning/{data['id']}/submit", json={"answers": [0]}).status_code == 403
        assert bob.post(f"/api/learning/generate/{kind}", json={"document_ids": [doc_id]}).status_code == 403


def test_unsupported_evidence(signed_client, monkeypatch):
    from services import learning_service
    doc_id = upload(signed_client)
    model = Mock()
    model.with_structured_output.return_value.invoke.return_value = generated("quiz", True)
    monkeypatch.setattr(learning_service, "_get_chat_llm", lambda **kw: model)
    assert signed_client.post("/api/learning/generate/quiz", json={"document_ids": [doc_id]}).status_code == 502
    assert model.with_structured_output.return_value.invoke.call_count == 2
    assert signed_client.get("/api/learning").json() == []


def test_output_validation():
    invalid = generated("quiz")["questions"][0]
    invalid["options"] = ["same"] * 4
    with pytest.raises(ValidationError):
        QuizQuestion.model_validate(invalid)
    with pytest.raises(ValidationError):
        Flashcards.model_validate({"title": "empty", "cards": []})


def test_empty_learning_sources(signed_client, setup_app):
    from models import Document
    factory, _ = setup_app
    with factory() as db:
        user_id = signed_client.get("/api/auth/me").json()["id"]
        doc = Document(owner_id=user_id, filename="empty.txt", original_filename="empty.txt", file_path="empty.txt", status="failed")
        db.add(doc); db.commit(); doc_id = doc.id
    assert signed_client.post("/api/learning/generate/notes", json={"document_ids": [doc_id]}).status_code == 422


def test_flashcard_citation_repaired_only_when_quote_exists(signed_client, monkeypatch):
    from services import learning_service
    doc_id = upload(signed_client)
    draft = generated("flashcards")
    draft["cards"][0]["evidence"]["source_number"] = 99
    model = Mock()
    model.with_structured_output.return_value.invoke.return_value = draft
    monkeypatch.setattr(learning_service, "_get_chat_llm", lambda **kw: model)
    response = signed_client.post("/api/learning/generate/flashcards", json={"document_ids": [doc_id], "count": 1})
    assert response.status_code == 201, response.text
    assert response.json()["content"]["cards"][0]["evidence"]["source_number"] == 1


def test_flashcard_bad_evidence_gets_one_grounded_retry(signed_client, monkeypatch):
    from services import learning_service
    doc_id = upload(signed_client)
    model = Mock()
    model.with_structured_output.return_value.invoke.side_effect = [generated("flashcards", True), generated("flashcards")]
    monkeypatch.setattr(learning_service, "_get_chat_llm", lambda **kw: model)
    response = signed_client.post("/api/learning/generate/flashcards", json={"document_ids": [doc_id], "count": 1})
    assert response.status_code == 201, response.text
    assert model.with_structured_output.return_value.invoke.call_count == 2
    assert signed_client.get("/api/learning").json()[0]["id"] == response.json()["id"]
