from types import SimpleNamespace
import httpx
import pytest
from openai import AuthenticationError, RateLimitError, APIConnectionError
from services.errors import IndexingServiceError, indexing_error_message


def provider_response(status):
    return httpx.Response(status, request=httpx.Request("POST", "https://api.openai.com/v1/embeddings"))


@pytest.mark.parametrize("exception,expected", [
    (AuthenticationError("PRIVATE PROVIDER DETAIL", response=provider_response(401), body=None), "API key"),
    (RateLimitError("PRIVATE PROVIDER DETAIL", response=provider_response(429), body={"code": "insufficient_quota"}), "billing"),
    (APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/embeddings")), "Cannot connect to OpenAI"),
    (TimeoutError("PRIVATE PROVIDER DETAIL"), "timed out"),
])
def test_safe_actionable_embedding_errors(exception, expected):
    message = indexing_error_message(IndexingServiceError("embeddings", exception))
    assert expected in message
    assert "PRIVATE" not in message


def test_qdrant_error_does_not_expose_internal_exception():
    message = indexing_error_message(IndexingServiceError("qdrant", RuntimeError("PRIVATE storage details")))
    assert "QDRANT_PATH" in message
    assert "one local app instance" in message
    assert "PRIVATE" not in message


def test_embeddings_do_not_require_tokenizer_download(monkeypatch):
    from langchain_openai import OpenAIEmbeddings
    from services.embedding_service import get_embeddings
    get_embeddings.cache_clear()
    try:
        embeddings = get_embeddings()
        seen = []
        def tokenize(*args, **kwargs):
            pytest.fail("Already chunked text must not invoke the downloadable tokenizer")
        def create(**kwargs):
            seen.append(kwargs["input"])
            return {"data": [{"embedding": [1.0, 0.0]} for _ in kwargs["input"]]}
        monkeypatch.setattr(OpenAIEmbeddings, "_tokenize", tokenize)
        monkeypatch.setattr(embeddings, "client", SimpleNamespace(create=create))
        assert embeddings.embed_documents(["A small document chunk."]) == [[1.0, 0.0]]
        assert seen == [["A small document chunk."]]
    finally:
        get_embeddings.cache_clear()


def test_upload_shows_openai_auth_error(signed_client, setup_app, monkeypatch):
    _, backend = setup_app
    def fail(texts):
        raise AuthenticationError("PRIVATE PROVIDER DETAIL", response=provider_response(401), body=None)
    monkeypatch.setattr(backend.embeddings, "embed_documents", fail)
    response = signed_client.post("/api/upload", files={"files": ("notes.txt", b"Document with study content.", "text/plain")})
    assert response.status_code == 201
    doc = response.json()["documents"][0]
    assert doc["status"] == "failed"
    assert "OPENAI_API_KEY" in doc["error_message"]
    assert "PRIVATE" not in response.text
