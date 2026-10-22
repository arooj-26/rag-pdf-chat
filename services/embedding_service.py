"""
services/embedding_service.py
-------------------------------
Thin wrapper around LangChain's `OpenAIEmbeddings`, exposed as a
cached singleton so the embedding client (and its connection pool)
is reused across requests instead of being recreated on every call.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from config import get_settings

settings = get_settings()


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """Return a cached OpenAIEmbeddings client configured from settings."""
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key or None,
        dimensions=settings.embedding_dimensions,
        request_timeout=settings.request_timeout,
        max_retries=2,
        # The ingestion pipeline already bounds/splits text. Send those strings
        # directly instead of downloading a separate tokenizer on first upload.
        check_embedding_ctx_length=False,
        chunk_size=64,
    )
