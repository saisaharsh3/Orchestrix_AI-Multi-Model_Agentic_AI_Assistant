"""
orchestrator.py - Routes one user message through the handler pipeline.

The routing logic lives in core/handlers/; this module owns the per-request
plumbing: session lookup, per-user locking, conversation memory, error
handling and the research trace (research/logs/orchestration_trace.jsonl).
"""

import json
import time
import uuid
from pathlib import Path

from config.settings import settings
from core.handlers import PIPELINE, ReminderTarget, Reply, Request
from core.handlers.base import STAGE_FALLBACK
from core.logger import get_logger
from core.session import sessions
from models.errors import LLMError

logger = get_logger(__name__)

TRACE_FILE = Path("research/logs/orchestration_trace.jsonl")


def log_orchestration_event(event: dict) -> None:
    """Append one trace event (JSONL) for the research experiments."""
    if not settings.ENABLE_RESEARCH_TRACE:
        return
    try:
        TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError as e:
        logger.debug(f"Failed to log orchestration event: {e}")


def respond(
    user_input: str,
    user_id: str | None = None,
    model_type: str | None = None,
    use_web: bool | None = None,
    use_pdf: bool | None = None,
    pdf_store=None,
    reminder_target: ReminderTarget | None = None,
) -> Reply:
    """
    Handle one message. Arguments left as None come from the user's session,
    so callers normally pass only the text and user_id.
    """
    session = sessions.get(user_id)
    text = user_input.strip()
    start = time.time()

    with session.lock:
        req = Request(
            text=text,
            session=session,
            model_type=model_type or session.model_type,
            use_web=session.use_web if use_web is None else use_web,
            use_pdf=session.use_pdf if use_pdf is None else use_pdf,
            reminder_target=reminder_target,
        )
        if req.use_pdf:
            req.pdf_store = pdf_store or session.pdf_store
        req.trace = {
            "request_id": str(uuid.uuid4()),
            "timestamp": start,
            "input": text[:100],
            "model_type": req.model_type,
        }
        logger.info(
            "Processing request",
            extra={"user_id": session.user_id, "input_length": len(text), "model": req.model_type},
        )

        reply = _run_pipeline(req)
        session.memory.add_turn(text, reply.text)

    req.trace.update(
        stage_reached=reply.stage,
        stages_executed=[reply.stage],
        confidence=reply.confidence,
        total_latency_ms=int((time.time() - start) * 1000),
    )
    log_orchestration_event(req.trace)
    return reply


def _run_pipeline(req: Request) -> Reply:
    try:
        for handler in PIPELINE:
            result = handler(req)
            if result is None:
                continue
            return result if isinstance(result, Reply) else Reply(str(result))
    except LLMError as e:
        logger.warning(f"Model error: {e}")
        return Reply(f"The model could not answer right now: {str(e)[:200]}", stage=STAGE_FALLBACK)
    except Exception as e:
        logger.error(f"Unhandled error while processing request: {e}", exc_info=True)
        return Reply(f"Something went wrong: {str(e)[:200]}", stage=STAGE_FALLBACK)
    return Reply("Sorry, I didn't understand that.", stage=STAGE_FALLBACK)


def generate_response(
    user_input: str,
    model_type: str | None = None,
    pdf_store=None,
    use_web: bool | None = None,
    use_pdf: bool | None = None,
    user_id: str | None = None,
) -> str:
    """Text-only wrapper around respond(), kept for existing callers."""
    return respond(
        user_input,
        user_id=user_id,
        model_type=model_type,
        use_web=use_web,
        use_pdf=use_pdf,
        pdf_store=pdf_store,
    ).text
