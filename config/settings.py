"""
config/settings.py - Centralized configuration and per-user preferences.

Every environment variable the app reads is declared here; other modules
import `settings` instead of calling os.getenv themselves.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _id_set(name: str) -> frozenset[str]:
    raw = os.getenv(name, "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


class Settings:
    """Global settings, read once from the environment."""

    def __init__(self):
        # Paths
        self.DATA_DIR = Path(os.getenv("ORCHESTRIX_DATA_DIR", "data"))
        self.DB_PATH = Path(os.getenv("ORCHESTRIX_DB_PATH", str(self.DATA_DIR / "orchestrix.db")))
        self.CREDENTIALS_DIR = Path(os.getenv("GOOGLE_CREDENTIALS_DIR", "credentials"))

        # API keys
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

        # Telegram. TELEGRAM_TOKEN is accepted for older .env files.
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        # Users allowed to talk to the bot. Falls back to TELEGRAM_CHAT_ID
        # (in a private chat the chat id equals the user id).
        allowed = _id_set("TELEGRAM_ALLOWED_USER_IDS")
        if not allowed and self.TELEGRAM_CHAT_ID:
            allowed = frozenset({self.TELEGRAM_CHAT_ID})
        self.TELEGRAM_ALLOWED_USER_IDS = allowed
        self.TELEGRAM_ALLOW_ALL = _bool("TELEGRAM_ALLOW_ALL", False)

        # HTTP API
        self.API_TOKEN = os.getenv("ORCHESTRIX_API_TOKEN", "")

        # Models
        self.DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "local")  # "local" or "api"
        self.OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
        self.OLLAMA_NUM_GPU = _int("OLLAMA_NUM_GPU", 20)
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
        # Fall back from Gemini to the local model when the API quota is exhausted.
        self.API_QUOTA_FALLBACK_TO_LOCAL = _bool("API_QUOTA_FALLBACK_TO_LOCAL", True)
        # Let Gemini pick a read-only tool when no pattern matched (API mode only).
        self.ENABLE_LLM_TOOL_ROUTING = _bool("ENABLE_LLM_TOOL_ROUTING", True)

        # Agent mode (/agent) and the MCP server
        self.AGENT_MAX_STEPS = _int("AGENT_MAX_STEPS", 6)
        self.MCP_USER_ID = os.getenv("ORCHESTRIX_MCP_USER", "") or self.TELEGRAM_CHAT_ID or "mcp"
        self.MCP_ALLOW_WRITE = _bool("ORCHESTRIX_MCP_ALLOW_WRITE", False)

        # Feature toggles
        self.ENABLE_WEB_SEARCH = _bool("ENABLE_WEB_SEARCH", True)
        self.ENABLE_VOICE = _bool("ENABLE_VOICE", True)
        self.ENABLE_PDF_RAG = _bool("ENABLE_PDF_RAG", True)
        self.ENABLE_PHONE_ADB = _bool("ENABLE_PHONE_ADB", True)
        self.ENABLE_RESEARCH_TRACE = _bool("ENABLE_RESEARCH_TRACE", True)
        # Block URL tools from fetching localhost / private network addresses.
        self.ALLOW_PRIVATE_URLS = _bool("ALLOW_PRIVATE_URLS", False)

        # Rate limiting (requests per minute)
        self.GEMINI_RATE_LIMIT = _int("GEMINI_RATE_LIMIT", 60)
        self.WEB_SEARCH_RATE_LIMIT = _int("WEB_SEARCH_RATE_LIMIT", 30)
        self.MAPS_RATE_LIMIT = _int("MAPS_RATE_LIMIT", 50)
        self.NEWS_RATE_LIMIT = _int("NEWS_RATE_LIMIT", 30)

        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

        # Locale defaults
        self.TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
        self.DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Hyderabad")
        self.DEFAULT_LAT = _float("DEFAULT_LAT", 17.385)
        self.DEFAULT_LON = _float("DEFAULT_LON", 78.4867)
        self.DAILY_BRIEFING_HOUR = _int("DAILY_BRIEFING_HOUR", 8)

        # Behaviour
        self.DEFAULT_TONE = "formal"
        self.MEMORY_WINDOW = _int("MEMORY_WINDOW", 15)  # turns used for context


settings = Settings()


class UserPreferences:
    """Per-user preferences, persisted in the SQLite store."""

    NAMESPACE = "user_prefs"

    @staticmethod
    def _store():
        from core.storage import get_store
        return get_store()

    @staticmethod
    def get_user_prefs(user_id: str) -> dict[str, Any]:
        store = UserPreferences._store()
        prefs = store.get(UserPreferences.NAMESPACE, user_id)
        if prefs is None:
            prefs = UserPreferences.get_default_prefs(user_id)
            store.put(UserPreferences.NAMESPACE, user_id, prefs)
        return prefs

    @staticmethod
    def set_user_pref(user_id: str, key: str, value: Any) -> None:
        prefs = UserPreferences.get_user_prefs(user_id)
        prefs[key] = value
        prefs["last_active"] = datetime.now().isoformat()
        UserPreferences._store().put(UserPreferences.NAMESPACE, user_id, prefs)

    @staticmethod
    def get_default_prefs(user_id: str) -> dict[str, Any]:
        now = datetime.now().isoformat()
        return {
            "user_id": user_id,
            "preferred_model": settings.DEFAULT_MODEL,
            "default_tone": settings.DEFAULT_TONE,
            "language": "en",
            "timezone": settings.TIMEZONE,
            "location": {
                "lat": settings.DEFAULT_LAT,
                "lon": settings.DEFAULT_LON,
                "name": settings.DEFAULT_CITY,
            },
            "privacy_mode": False,
            "auto_web_search": settings.ENABLE_WEB_SEARCH,
            "enable_voice": settings.ENABLE_VOICE,
            "enable_pdf_rag": settings.ENABLE_PDF_RAG,
            # Linguistic masking before cloud calls (Experiment 5). Off by default.
            "stealth_mode": False,
            "created_at": now,
            "last_active": now,
        }

    @staticmethod
    def toggle_stealth_mode(user_id: str, enabled: bool) -> None:
        UserPreferences.set_user_pref(user_id, "stealth_mode", enabled)
