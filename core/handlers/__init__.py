"""
Request handlers, tried in order until one returns a reply.

Order matters:
  1. commands and "stop"                 – always win
  2. pending confirmations / dialogues   – capture YES/NO and follow-up answers
  3. deterministic intent handlers       – cheap, no model needed to route
  4. retrieval (PDF, Wikipedia)
  5. fallback answer (web search + LLM, with Gemini tool routing in API mode)
"""

from core.handlers import calendar, commands, email, features, knowledge, phone, tasks, utilities
from core.handlers.base import Handler, ReminderTarget, Reply, Request

PIPELINE: list[Handler] = [
    commands.handle,
    phone.handle_stop,
    email.handle_pending,
    calendar.handle_pending,
    phone.handle_booking,
    features.handle,
    utilities.handle,  # before tasks: "remind me to X at 5pm" is a reminder
    tasks.handle,      # before calendar: "add task X tomorrow at 5pm" is a task
    email.handle,
    calendar.handle,
    phone.handle,
    knowledge.handle_rag,
    knowledge.handle_fact,
    knowledge.handle_fallback,
]

__all__ = ["PIPELINE", "Reply", "ReminderTarget", "Request"]
