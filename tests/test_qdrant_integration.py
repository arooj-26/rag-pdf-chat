"""Opt-in server test: QDRANT_TEST_URL=http://localhost:6333 python -m pytest -m integration."""
import os
from uuid import uuid4
import pytest
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from evaluation.embeddings import FixtureEmbeddings
from services.vector_store import QdrantBackend


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("QDRANT_TEST_URL"), reason="QDRANT_TEST_URL is not configured")
def test_real_qdrant_server():
    client = QdrantClient(url=os.environ["QDRANT_TEST_URL"], timeout=10)
    collection = "test_research_" + uuid4().hex
    backend = QdrantBackend(client, FixtureEmbeddings(), collection, 64)
    try:
        docs = [Document(page_content="ATP biology", metadata={"owner_id": "alice", "document_id": "d1", "chunk_id": "d1:0", "chunk_index": 0}), Document(page_content="secret ATP", metadata={"owner_id": "bob", "document_id": "d2", "chunk_id": "d2:0", "chunk_index": 0})]
        backend.ingest(docs)
        assert all(d.metadata["owner_id"] == "alice" for d in backend.search("ATP", "alice", ["d1", "d2"], 10))
        backend.delete("d1", "alice")
        assert backend.search("ATP", "alice", ["d1"], 10) == []
    finally:
        if client.collection_exists(collection): client.delete_collection(collection)
        client.close()
