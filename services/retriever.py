"""LangChain retriever retaining the original application integration point."""
from langchain_core.retrievers import BaseRetriever
from config import get_settings
from database import db_session
from services.hybrid_retrieval import retrieve

class ResearchRetriever(BaseRetriever):
    owner_id: str
    document_id: str | None = None
    k: int = 4

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        with db_session() as db:
            return retrieve(db, self.owner_id, query, [self.document_id] if self.document_id else None, k=self.k)


def get_retriever(document_id: str | None = None, k: int | None = None, *, owner_id: str):
    return ResearchRetriever(owner_id=owner_id, document_id=document_id, k=k or get_settings().retriever_k)
