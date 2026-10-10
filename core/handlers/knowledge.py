"""
Answering questions: PDF RAG, Wikipedia facts, web search, and the final
model call (with Gemini tool routing in API mode).
"""

from config.settings import UserPreferences, settings
from core.handlers.base import STAGE_FALLBACK, STAGE_LLM_ROUTING, STAGE_RETRIEVAL, Reply, Request
from core.logger import get_logger
from core.model_manager import generate_llm
from core.prompt_builder import build_general_prompt, build_rag_prompt, build_web_prompt
from core.rate_limiter import news_limiter, web_limiter
from core.stylometric_defense import StyleometricDefense
from core.tone_controller import tone_instruction
from models.errors import LLMError
from tools.news_search import news_search
from tools.web_search import web_search
from tools.wiki_search import wiki_search

logger = get_logger(__name__)

_FACT_MARKERS = ("who is", "current", "cm of", "chief minister", "prime minister", "president")

LOCAL_UNAVAILABLE = (
    "The local model is not responding ({error}).\n\n"
    "Your message was NOT sent to the cloud. Try again in a moment, "
    "or send /api to use Gemini for this session."
)


def is_fact_question(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _FACT_MARKERS)


def handle_rag(req: Request) -> Reply | None:
    if not req.use_pdf or req.pdf_store is None:
        return None
    chunks = req.pdf_store.smart_search(req.text, top_k=8) or req.pdf_store.text_chunks[:6]
    if not chunks:
        return Reply("No content found in the PDF. Try rephrasing your question.", stage=STAGE_RETRIEVAL)
    prompt = build_rag_prompt(req.text, chunks, req.model_type)
    return Reply(_generate(req, prompt), stage=STAGE_RETRIEVAL)


def handle_fact(req: Request) -> Reply | None:
    if not is_fact_question(req.text):
        return None
    fact = wiki_search(req.text)
    return Reply(fact, stage=STAGE_RETRIEVAL) if fact else None


def handle_fallback(req: Request) -> Reply:
    news, web = [], []
    if req.use_web:
        news_limiter.wait_if_needed("news")
        news = news_search(req.text)
        web_limiter.wait_if_needed("web")
        web = web_search(req.text)

    query = req.text
    if req.model_type == "api" and UserPreferences.get_user_prefs(req.user_id).get("stealth_mode"):
        # Strip stylometric markers before the text leaves the device (Experiment 5).
        query = StyleometricDefense.normalize_style(req.text)

    tone = tone_instruction(req.session.tone)
    context = [f"TONE: {tone}"] if tone else []
    if news or web:
        prompt = build_web_prompt(query, news, web, req.model_type)
        if tone:
            prompt = f"TONE: {tone}\n\n{prompt}"
    else:
        prompt = build_general_prompt(query, context, req.model_type)

    if req.model_type == "api" and settings.ENABLE_LLM_TOOL_ROUTING and settings.GEMINI_API_KEY:
        from core.agent.tools import ToolContext
        from core.tool_router import route_or_answer
        try:
            text, tool = route_or_answer(prompt, ToolContext(user_id=req.user_id, session=req.session))
            if text:
                return Reply(text, stage=STAGE_LLM_ROUTING if tool else STAGE_FALLBACK, confidence=0.3)
        except LLMError as e:
            logger.warning(f"Tool routing failed, falling back to plain generation: {e}")

    return Reply(_generate(req, prompt), stage=STAGE_FALLBACK, confidence=0.3)


def _generate(req: Request, prompt: str) -> str:
    try:
        return generate_llm(prompt, req.model_type)
    except LLMError as e:
        if req.model_type == "local":
            # Privacy boundary: never fall back to the cloud without the user's say-so.
            req.trace["local_failed"] = True
            return LOCAL_UNAVAILABLE.format(error=str(e)[:250])
        raise
