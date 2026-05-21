from models.local_llm import local_generate, local_generate_rag
from models.gemini_llm import gemini_generate

# ✅ NEW: Logging and Rate Limiting
from core.logger import get_logger
from core.rate_limiter import with_rate_limit, with_retry, gemini_limiter

logger = get_logger(__name__)

# If these strings appear in the prompt, use RAG mode (low temperature)
_RAG_SIGNALS = ["document excerpts", "pdf chunks", "pdf content", "[1]", "[2]", "[3]"]

def _is_rag_prompt(prompt: str) -> bool:
    p = prompt.lower()
    return any(sig.lower() in p for sig in _RAG_SIGNALS)

@with_rate_limit("gemini", gemini_limiter)
@with_retry(max_attempts=3, backoff_factor=1.5)
def _gemini_safe(prompt: str) -> str:
    """Call Gemini with rate limiting and automatic retry"""
    logger.debug(f"Calling Gemini API", extra={"prompt_length": len(prompt)})
    return gemini_generate(prompt)

def generate_llm(prompt: str, model_type: str = "api") -> str:
    try:
        if model_type == "local":
            logger.debug(f"Using local model", extra={"rag_mode": _is_rag_prompt(prompt)})
            if _is_rag_prompt(prompt):
                return local_generate_rag(prompt)
            return local_generate(prompt)
        else:
            # ✅ NEW: Use rate-limited, retrying Gemini call
            try:
                return _gemini_safe(prompt)
            except Exception as api_error:
                # ✅ NEW: Fallback to local model if API fails (quota exceeded, etc)
                error_str = str(api_error).lower()
                if any(keyword in error_str for keyword in ["quota", "resource_exhausted", "429", "limit"]):
                    logger.warning(
                        f"API quota/limit exceeded, automatically falling back to local model",
                        extra={"error": str(api_error)[:100]}
                    )
                    if _is_rag_prompt(prompt):
                        return local_generate_rag(prompt)
                    return local_generate(prompt)
                else:
                    raise

    except Exception as e:
        logger.error(f"LLM generation failed", exc_info=True, extra={
            "model": model_type,
            "error_type": type(e).__name__
        })
        return f"Error generating response: {str(e)[:100]}"
        # Auto fallback if Gemini quota exhausted
        if "RESOURCE_EXHAUSTED" in str(e):
            logger.warning("Gemini quota exhausted — falling back to local model")
            if _is_rag_prompt(prompt):
                return local_generate_rag(prompt)
            return local_generate(prompt)
        raise e