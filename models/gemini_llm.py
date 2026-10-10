"""
gemini_llm.py - Google Gemini (cloud) backend.

The client is created on first use, so importing this module never fails
just because GEMINI_API_KEY is missing.
"""

import threading

from config.settings import settings
from models.errors import LLMError, QuotaExceededError

_client = None
_client_lock = threading.Lock()

_QUOTA_MARKERS = ("quota", "resource_exhausted", "429", "rate limit")


def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            if not settings.GEMINI_API_KEY:
                raise LLMError("GEMINI_API_KEY is not set. Add it to .env or use the local model (/local).")
            from google import genai
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return _client


def _wrap(e: Exception) -> LLMError:
    if isinstance(e, LLMError):
        return e
    if any(marker in str(e).lower() for marker in _QUOTA_MARKERS):
        return QuotaExceededError(str(e))
    return LLMError(f"Gemini request failed: {e}")


def gemini_generate(prompt: str) -> str:
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
    except Exception as e:
        raise _wrap(e) from e
    text = (response.text or "").strip()
    if not text:
        raise LLMError("Gemini returned an empty response.")
    return text


def gemini_generate_or_call(prompt: str, declarations: list[dict]):
    """
    Generate with native function calling available.

    `declarations` are {"name", "description", "parameters": <schema>} dicts.
    Returns ("text", str) when Gemini answers directly, or
    ("call", (name, args)) when it picks a function. Nothing is executed here.
    """
    from google.genai import types

    tool = types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in declarations])
    config = types.GenerateContentConfig(
        tools=[tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
    except Exception as e:
        raise _wrap(e) from e

    calls = response.function_calls or []
    if calls:
        return "call", (calls[0].name, dict(calls[0].args or {}))
    text = (response.text or "").strip()
    if not text:
        raise LLMError("Gemini returned an empty response.")
    return "text", text
