"""
model_manager.py - Single entry point for text generation.

generate_llm() raises models.errors.LLMError on failure instead of returning
an error string, so callers can never mistake a failure for an answer.

Privacy rule: a "local" request is never sent to the cloud automatically.
The only automatic switch is the other direction (Gemini quota exhausted →
local model), which keeps data on-device and can be disabled with
API_QUOTA_FALLBACK_TO_LOCAL=false.
"""

from config.settings import settings
from core.logger import get_logger
from core.rate_limiter import RateLimiter, with_rate_limit, with_retry
from models.errors import LLMError, QuotaExceededError

logger = get_logger(__name__)

gemini_limiter = RateLimiter(calls_per_minute=settings.GEMINI_RATE_LIMIT)

# If these strings appear in the prompt, use RAG mode (low temperature)
_RAG_SIGNALS = ["document excerpts", "pdf chunks", "pdf content", "[1]", "[2]", "[3]"]


def _is_rag_prompt(prompt: str) -> bool:
    p = prompt.lower()
    return any(sig in p for sig in _RAG_SIGNALS)


@with_rate_limit("gemini", gemini_limiter)
@with_retry(max_attempts=3, backoff_factor=1.5, retry_on=(LLMError,), give_up_on=(QuotaExceededError,))
def _gemini(prompt: str) -> str:
    from models.gemini_llm import gemini_generate
    return gemini_generate(prompt)


def _local(prompt: str) -> str:
    from models.local_llm import local_generate, local_generate_rag
    if _is_rag_prompt(prompt):
        return local_generate_rag(prompt)
    return local_generate(prompt)


def generate_llm(prompt: str, model_type: str = "api") -> str:
    if model_type == "local":
        return _local(prompt)

    try:
        return _gemini(prompt)
    except QuotaExceededError:
        if not settings.API_QUOTA_FALLBACK_TO_LOCAL:
            raise
        logger.warning("Gemini quota exhausted; answering with the local model instead")
        return _local(prompt)
