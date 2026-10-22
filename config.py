"""
config.py
---------
Centralized application configuration using Pydantic v2 Settings.

All configuration is loaded from environment variables (and a local
`.env` file during development). This module exposes a single cached
`get_settings()` accessor so configuration is read once and shared
across the whole application.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application-wide settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = Field(default="AI Research & Study Assistant")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    app_version: str = Field(default="1.0.0")

    # --- OpenAI ---
    openai_api_key: str = Field(default="")
    openai_chat_model: str = Field(default="gpt-4o-mini")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    # --- Database ---
    database_url: str = Field(default=f"sqlite:///{BASE_DIR}/data/pdf_chat.db")

    # --- Storage paths ---
    upload_dir: Path = Field(default=BASE_DIR / "data" / "uploads")
    vector_store_dir: Path = Field(default=BASE_DIR / "data" / "vector_store")

    # --- RAG / Chunking ---
    chunk_size: int = Field(default=1000, ge=100, le=8000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)
    retriever_k: int = Field(default=4, ge=1, le=20)

    # --- Uploads ---
    max_upload_size_mb: int = Field(default=25, ge=1, le=200)
    allowed_extensions: List[str] = Field(default_factory=lambda: [".pdf", ".docx", ".txt", ".md"])

    # --- CORS ---
    allowed_origins: List[str] = Field(default_factory=list)

    # --- Security ---
    secret_key: str = Field(default="change-this-secret-key-in-production")

    cookie_secure: bool = False
    session_hours: int = Field(default=24, ge=1, le=168)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_path: str = ""
    qdrant_collection: str = "research_chunks"
    embedding_dimensions: int = Field(default=1536, ge=1)
    request_timeout: float = Field(default=30, ge=1, le=120)
    retrieval_mode: str = "hybrid"
    retrieval_candidates: int = Field(default=20, ge=1, le=100)
    rrf_constant: int = Field(default=60, ge=1)
    rerank_enabled: bool = False
    ocr_enabled: bool = False
    ocr_language: str = "eng"
    max_document_pages: int = Field(default=300, ge=1, le=1000)
    max_extracted_characters: int = Field(default=2_000_000, ge=1000)
    max_output_tokens: int = Field(default=2000, ge=100, le=8000)
    requests_per_minute: int = Field(default=60, ge=1)

    @model_validator(mode="after")
    def validate_settings(self):
        if "*" in self.allowed_origins:
            raise ValueError("Credentialed CORS requires explicit origins")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.retrieval_mode not in {"semantic", "keyword", "hybrid"}:
            raise ValueError("Invalid RETRIEVAL_MODE")
        if self.app_env == "production" and (len(self.secret_key) < 32 or self.secret_key.startswith("change-") or not self.cookie_secure):
            raise ValueError("Production requires random SECRET_KEY and COOKIE_SECURE=true")
        return self

    # --- Conversation memory ---
    max_history_messages: int = Field(default=12, ge=2, le=100)

    @field_validator("openai_api_key")
    @classmethod
    def _warn_if_missing_key(cls, value: str) -> str:
        # We intentionally do not raise here so the app can still boot
        # (e.g. to serve the health check) without a key configured.
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create all directories required by the application at startup."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide Settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
