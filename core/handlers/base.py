"""
Shared types for request handlers.

A handler is a function `handle(req: Request) -> Reply | str | None`.
Returning None means "not mine"; the orchestrator then tries the next
handler in core/handlers/__init__.py:PIPELINE.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.session import Session

# Orchestration stages (used by research/exp1_orchestration_efficiency.py)
STAGE_COMMAND = 0     # slash commands, no model involved
STAGE_PATTERN = 1     # deterministic pattern-matched handlers
STAGE_LLM_ROUTING = 2 # Gemini function calling picked a tool
STAGE_RETRIEVAL = 3   # RAG / wiki lookups
STAGE_FALLBACK = 4    # general LLM answer


@dataclass
class ReminderTarget:
    """Where scheduled reminders are delivered (Telegram only)."""
    bot: Any
    chat_id: str


@dataclass
class Request:
    text: str
    session: Session
    model_type: str
    use_web: bool
    use_pdf: bool
    pdf_store: Any = None
    reminder_target: ReminderTarget | None = None
    trace: dict = field(default_factory=dict)

    @property
    def lower(self) -> str:
        return self.text.lower()

    @property
    def user_id(self) -> str:
        return self.session.user_id


@dataclass
class Reply:
    text: str
    files: list[str] = field(default_factory=list)  # paths to send as documents
    stage: int = STAGE_PATTERN
    confidence: float | None = None


Handler = Callable[[Request], "Reply | str | None"]
