"""Offline test isolation: no local user data, network or paid model calls."""
import os
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test-placeholder"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import hashlib
import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import database
from database import Base, get_db
from main import app
from services.vector_store import QdrantBackend


class FakeEmbeddings(Embeddings):
    """Stable toy hash embeddings, intentionally not a semantic quality benchmark."""
    def embed_query(self, text):
        import re
        vector = [0.0] * 16
        for word in re.findall(r"[\w-]+", text.lower()):
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % 16] += 1
        return vector

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]


@pytest.fixture
def setup_app(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    def dependency():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    monkeypatch.setattr(database, "SessionLocal", factory)
    from config import get_settings
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    from services import vector_store, hybrid_retrieval, ingestion, document_updates, request_guard
    backend = QdrantBackend(QdrantClient(":memory:"), FakeEmbeddings(), "test", 16)
    for module in (vector_store, hybrid_retrieval, ingestion, document_updates):
        monkeypatch.setattr(module, "get_backend", lambda: backend)
    request_guard._buckets.clear()
    yield factory, backend
    app.dependency_overrides.clear()
    backend.client.close()
    engine.dispose()


@pytest.fixture
def client(setup_app):
    with TestClient(app) as client:
        yield client


def account(client, email="alice@example.com"):
    response = client.post("/api/auth/register", json={"email": email, "password": "a-long-safe-password"})
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


@pytest.fixture
def signed_client(client):
    account(client)
    return client
