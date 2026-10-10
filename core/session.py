"""
core/session.py - Per-user conversation state.

Everything that used to live in module-level globals (pending email/calendar
confirmations, the booking flow, tone, model and toggles, the PDF store)
lives on a Session, so two users can never see or confirm each other's
pending actions.
"""

import threading
from dataclasses import dataclass, field
from typing import Any

from config.settings import UserPreferences, settings
from core.conversation_memory import ConversationMemory
from core.tone_controller import is_valid_tone


def _empty_email() -> dict:
    return {
        "pending": False,
        "action": "send",
        "to": "",
        "subject": "",
        "body": "",
        "tone": "professional",
        "msg_id": "",
        "use_ai": False,
        "original_input": "",
    }


def _empty_calendar() -> dict:
    return {"pending": False, "title": "", "start": None, "end": None, "location": ""}


def _empty_booking() -> dict:
    return {"active": False, "type": None, "step": None, "data": {}}


@dataclass
class Session:
    user_id: str
    model_type: str = field(default_factory=lambda: settings.DEFAULT_MODEL)
    use_web: bool = field(default_factory=lambda: settings.ENABLE_WEB_SEARCH)
    use_pdf: bool = False
    tone: str = field(default_factory=lambda: settings.DEFAULT_TONE)
    email: dict = field(default_factory=_empty_email)
    calendar: dict = field(default_factory=_empty_calendar)
    booking: dict = field(default_factory=_empty_booking)
    recent_pdfs: list[str] = field(default_factory=list)
    _pdf_store: Any = None
    # Serialises requests from the same user (the bot handles updates concurrently).
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self):
        self.memory = ConversationMemory(self.user_id)

    @property
    def pdf_store(self):
        """Created lazily: loading the embedding model is slow."""
        if self._pdf_store is None:
            from rag.vector_store import PDFVectorStore
            base = settings.DATA_DIR / "rag" / _safe(self.user_id)
            self._pdf_store = PDFVectorStore(
                pdf_dir=str(self.pdf_dir),
                index_path=str(base / "index.faiss"),
                meta_path=str(base / "chunks.json"),
            )
        return self._pdf_store

    @pdf_store.setter
    def pdf_store(self, store) -> None:
        self._pdf_store = store

    @property
    def pdf_dir(self):
        path = settings.DATA_DIR / "pdfs" / _safe(self.user_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def reset_email(self) -> None:
        self.email = _empty_email()

    def reset_calendar(self) -> None:
        self.calendar = _empty_calendar()

    def reset_booking(self) -> None:
        self.booking = _empty_booking()


def _safe(user_id: str) -> str:
    return "".join(c for c in str(user_id) if c.isalnum() or c in "-_") or "default"


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, user_id: str | None) -> Session:
        key = str(user_id) if user_id else "local"
        with self._lock:
            if key not in self._sessions:
                session = Session(user_id=key)
                prefs = UserPreferences.get_user_prefs(key)
                session.model_type = prefs.get("preferred_model", session.model_type)
                if is_valid_tone(prefs.get("default_tone", "")):
                    session.tone = prefs["default_tone"]
                self._sessions[key] = session
            return self._sessions[key]

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


sessions = SessionStore()
