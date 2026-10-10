"""
tool_router.py - Let Gemini pick a tool when no pattern handler matched.

The regex handlers cover the common phrasings; this catches the rest
("is it going to be hot in Pune?", "how's Infosys doing today?") using
Gemini's native function calling, over the READ tools of the shared
registry (core/agent/tools.py).

Anything that sends, books, deletes or calls stays behind the pattern
handlers, /agent, and their YES/NO confirmations. Used in API mode only,
so local-mode requests never leave the device.
"""

from config.settings import settings
from core.agent.tools import READ, TOOLS, ToolContext, tools_of
from core.logger import get_logger
from core.rate_limiter import with_retry
from models.errors import LLMError, QuotaExceededError

logger = get_logger(__name__)

ROUTER_PREAMBLE = (
    "If one of the available functions directly answers the user's request, call it. "
    "Otherwise answer the question yourself in text.\n\n"
)


@with_retry(max_attempts=3, backoff_factor=1.5, retry_on=(LLMError,), give_up_on=(QuotaExceededError,))
def _generate_or_call(prompt: str):
    from core.model_manager import gemini_limiter
    from models.gemini_llm import gemini_generate_or_call

    gemini_limiter.wait_if_needed("gemini")
    return gemini_generate_or_call(prompt, [t.gemini_declaration() for t in tools_of(READ)])


def route_or_answer(prompt: str, ctx: ToolContext | None = None) -> tuple[str, str | None]:
    """
    One Gemini call that either answers or picks a read-only tool.

    Returns (text, tool_name). tool_name is None when Gemini answered directly.
    Raises models.errors.LLMError on failure.
    """
    kind, payload = _generate_or_call(ROUTER_PREAMBLE + prompt)
    if kind == "text":
        return payload, None

    name, args = payload
    tool = TOOLS.get(name)
    if tool is None or tool.kind != READ:
        logger.warning(f"Gemini chose unavailable tool {name!r}")
        return "", None
    logger.info(f"LLM routing chose tool {name}", extra={"tool_args": args})
    try:
        return tool.execute(ctx or ToolContext(user_id=settings.MCP_USER_ID), args), name
    except (TypeError, ValueError) as e:
        logger.warning(f"Bad arguments for {name}: {args} ({e})")
        return "", None
