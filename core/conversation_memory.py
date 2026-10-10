"""
conversation_memory.py - Per-user multi-turn conversation memory.

Turns are persisted in SQLite (core/storage.py), so memory survives restarts
and one user's history is never visible to another user.
"""

import re

from config.settings import settings
from core.storage import get_store

_CITIES = [
    "hyderabad", "delhi", "bangalore", "mumbai", "pune", "goa", "kolkata", "jaipur",
    "lucknow", "chandigarh", "ahmedabad", "surat", "indore", "nagpur", "chennai",
]


class ConversationMemory:
    def __init__(self, user_id: str, store=None):
        self.user_id = user_id
        self._store = store

    @property
    def store(self):
        return self._store or get_store()

    def add_turn(self, user_input: str, assistant_response: str) -> None:
        self.store.add_turn(self.user_id, user_input, assistant_response)

    def recent(self, max_turns: int | None = None) -> list[dict]:
        return self.store.recent_turns(self.user_id, max_turns or settings.MEMORY_WINDOW)

    # ── user-facing history commands ───────────────────────────────────────
    def search_history(self, query: str, limit: int = 10) -> str:
        hits = self.store.search_turns(self.user_id, query, limit)
        if not hits:
            return f"No past messages mention '{query}'."
        lines = [f"Found {len(hits)} message(s) about '{query}':\n"]
        for turn in hits:
            lines.append(f"[{turn['timestamp'][:16].replace('T', ' ')}] You: {turn['user'][:120]}")
        return "\n".join(lines)

    def list_history(self, limit: int = 10) -> str:
        total = self.store.count_turns(self.user_id)
        if not total:
            return "No conversation history yet."
        lines = [f"Conversation history ({total} messages). Most recent:\n"]
        for turn in self.recent(limit):
            lines.append(f"[{turn['timestamp'][:16].replace('T', ' ')}] You: {turn['user'][:120]}")
        return "\n".join(lines)

    # ── context extraction used by handlers ────────────────────────────────
    def get_recent_location_context(self, max_turns: int = 15) -> str:
        context = ""
        for turn in self.recent(max_turns):
            user_msg = turn.get("user", "")
            if any(city in user_msg.lower() for city in _CITIES):
                context += f"User mentioned: {user_msg}\n"
        return context

    def get_recent_email_context(self, max_turns: int = 15) -> dict:
        context = {"recent_recipients": [], "recent_subjects": [], "email_tone": "professional"}
        for turn in self.recent(max_turns):
            user_msg = turn.get("user", "")
            lower = user_msg.lower()
            context["recent_recipients"].extend(re.findall(r"[\w.-]+@[\w.-]+\.\w+", user_msg))
            if re.search(r"subject|about|regarding", lower):
                context["recent_subjects"].append(user_msg)
            if any(t in lower for t in ["funny", "humor", "joke", "casual"]):
                context["email_tone"] = "casual"
            elif any(t in lower for t in ["formal", "professional", "official"]):
                context["email_tone"] = "professional"
        # Most recent first, so callers can take [0].
        context["recent_recipients"].reverse()
        return context

    def get_recent_calendar_context(self, max_turns: int = 15) -> dict:
        context = {"recent_events": [], "recent_dates": []}
        time_patterns = [
            r"\d{1,2}:\d{2}\s*(?:am|pm)",
            r"(?:today|tomorrow|next\s+(?:week|month)|monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        ]
        for turn in self.recent(max_turns):
            user_msg = turn.get("user", "")
            if any(kw in user_msg.lower() for kw in ["event", "meeting", "appointment", "call", "conference"]):
                context["recent_events"].append(user_msg)
            for pattern in time_patterns:
                context["recent_dates"].extend(re.findall(pattern, user_msg, re.IGNORECASE))
        return context

    def get_recent_phone_context(self, max_turns: int = 15) -> dict:
        context = {"recent_contacts": [], "recent_phone_numbers": []}
        for turn in self.recent(max_turns):
            user_msg = turn.get("user", "")
            context["recent_phone_numbers"].extend(
                re.findall(r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", user_msg)
            )
            context["recent_contacts"].extend(
                re.findall(r"\b(?:call|text|message|contact)\s+(\w+)", user_msg, re.IGNORECASE)
            )
        context["recent_phone_numbers"].reverse()
        context["recent_contacts"].reverse()
        return context

    def get_recent_web_context(self, max_turns: int = 15) -> dict:
        context = {"recent_urls": [], "recent_searches": []}
        for turn in self.recent(max_turns):
            user_msg = turn.get("user", "")
            context["recent_urls"].extend(re.findall(r"https?://\S+", user_msg))
            if any(kw in user_msg.lower() for kw in ["search", "find", "look up", "browse"]):
                context["recent_searches"].append(user_msg)
        context["recent_urls"].reverse()
        context["recent_searches"].reverse()
        return context

    def get_feature_context(self, feature: str, max_turns: int = 15) -> dict:
        feature = feature.lower()
        if feature == "maps":
            return {"location": self.get_recent_location_context(max_turns)}
        if feature == "email":
            return self.get_recent_email_context(max_turns)
        if feature == "calendar":
            return self.get_recent_calendar_context(max_turns)
        if feature == "phone":
            return self.get_recent_phone_context(max_turns)
        if feature == "web":
            return self.get_recent_web_context(max_turns)
        return {}
