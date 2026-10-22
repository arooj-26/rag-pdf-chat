"""Deterministic fixture embeddings, never used by the production application."""
import hashlib
import re
from langchain_core.embeddings import Embeddings


class FixtureEmbeddings(Embeddings):
    dimensions = 64

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in re.findall(r"[\w-]+", text.lower()):
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.dimensions] += 1.0
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]
