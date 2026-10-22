from langchain_core.documents import Document
from services.hybrid_retrieval import fuse, keyword_search


def test_fusion_metadata_and_deduplication():
    a = Document(page_content="Alpha", metadata={"chunk_id": "a", "owner_id": "alice", "section": "Terms"})
    b = Document(page_content="Beta", metadata={"chunk_id": "b"})
    result = fuse([[a, a, b], [b, a]], 10)
    assert len(result) == 2
    assert result[0].metadata["owner_id"] == "alice"
    assert result[0].metadata["section"] == "Terms"
    assert fuse([], 4) == []
    assert keyword_search("missing", [a, b], 4) == []
