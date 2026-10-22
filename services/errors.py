"""Safe provider error mapping; exception strings never enter API responses."""
from fastapi import HTTPException
from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, BadRequestError
from pydantic import ValidationError


class IndexingServiceError(RuntimeError):
    """Carry the failing stage without placing provider text in public errors."""
    def __init__(self, stage: str, original: Exception):
        super().__init__(f"{stage} operation failed")
        self.stage = stage
        self.original = original


def indexing_error_message(exc: Exception) -> str:
    stage = exc.stage if isinstance(exc, IndexingServiceError) else "indexing"
    original = exc.original if isinstance(exc, IndexingServiceError) else exc
    retry = " Restart the app after changing settings, then choose Reindex / retry in the dashboard."
    if isinstance(original, AuthenticationError):
        return "OpenAI rejected the API key. Check OPENAI_API_KEY in .env." + retry
    if isinstance(original, RateLimitError):
        if getattr(original, "code", None) in {"insufficient_quota", "billing_hard_limit_reached"}:
            return "OpenAI API credits or billing limit are exhausted. Check the API project's billing, then retry."
        return "OpenAI rate limit reached. Wait briefly, then retry indexing."
    if isinstance(original, (APITimeoutError, TimeoutError)):
        return "The indexing service timed out. Check connectivity, then retry."
    if isinstance(original, APIConnectionError):
        return "Cannot connect to OpenAI for embeddings. Check internet, proxy and firewall settings, then retry."
    if isinstance(original, BadRequestError):
        return "OpenAI rejected the embedding input or model settings. Check the embedding model and reduce CHUNK_SIZE if needed." + retry
    if stage == "qdrant":
        return "Qdrant storage or collection is unavailable. Check QDRANT_PATH or QDRANT_URL, use one local app instance, and verify embedding dimensions." + retry
    return "Indexing failed. Check the app terminal for the failing stage, then retry."


def provider_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IndexingServiceError):
        return HTTPException(503, indexing_error_message(exc))
    if isinstance(exc, AuthenticationError):
        return HTTPException(503, "AI provider credentials are unavailable. Contact the administrator.")
    if isinstance(exc, RateLimitError):
        return HTTPException(429, "AI provider quota or rate limit reached. Try again later.", headers={"Retry-After": "30"})
    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return HTTPException(504, "The service timed out. Please try again.")
    if isinstance(exc, ValidationError):
        return HTTPException(502, "AI output could not be validated. Please try again.")
    return HTTPException(503, "AI or document search service unavailable. Please try again.")
