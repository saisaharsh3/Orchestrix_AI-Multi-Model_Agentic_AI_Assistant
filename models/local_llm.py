"""
local_llm.py - On-device model via Ollama.

Model, host and GPU layer count come from .env (OLLAMA_MODEL, OLLAMA_HOST,
OLLAMA_NUM_GPU). On a CUDA / out-of-memory error the call is retried once on
CPU before giving up.
"""

import ollama

from config.settings import settings
from core.logger import get_logger
from models.errors import LLMError

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Orchestrix AI, a concise and accurate assistant.

Rules you must always follow:
- Answer in 1-3 short sentences unless more detail is needed.
- Never start with "I apologize", "Certainly!", "Of course!", "Based on the provided content".
- If asked to do a specific action like adding a task or setting a reminder, confirm it simply.
- Do not explain what you could do — just do it or say you cannot.
- If you don't know something, say "I don't know" — do not guess."""

RAG_SYSTEM_PROMPT = """You are a document Q&A assistant.
Answer ONLY using the document content provided.
If the answer is not in the document, say exactly: "Not found in the document."
Never guess or add outside knowledge."""

_client: ollama.Client | None = None


def _get_client() -> ollama.Client:
    global _client
    if _client is None:
        _client = ollama.Client(host=settings.OLLAMA_HOST)
    return _client


def _chat(prompt: str, system: str, options: dict) -> str:
    res = _get_client().chat(
        model=settings.OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        options=options,
    )
    text = res["message"]["content"].strip()
    if not text:
        raise LLMError("Local model returned an empty response.")
    return text


def _generate(prompt: str, system: str, temperature: float, top_p: float) -> str:
    options = {
        "temperature": temperature,
        "top_p": top_p,
        "repeat_penalty": 1.2,
        "num_gpu": settings.OLLAMA_NUM_GPU,
    }
    try:
        return _chat(prompt, system, options)
    except LLMError:
        raise
    except Exception as e:
        if "CUDA" not in str(e) and "500" not in str(e):
            raise LLMError(f"Local model error ({settings.OLLAMA_MODEL} at {settings.OLLAMA_HOST}): {e}") from e
        logger.warning(f"GPU inference failed ({e}); retrying on CPU")
        try:
            return _chat(prompt, system, {"temperature": temperature, "num_gpu": 0})
        except Exception as cpu_error:
            raise LLMError(f"Local model failed on GPU and CPU: {cpu_error}") from cpu_error


def local_generate(prompt: str) -> str:
    return _generate(prompt, SYSTEM_PROMPT, temperature=0.3, top_p=0.9)


def local_generate_rag(prompt: str) -> str:
    return _generate(prompt, RAG_SYSTEM_PROMPT, temperature=0.1, top_p=0.8)
