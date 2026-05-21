"""
config/settings.py - Centralized Configuration & User Preferences
Manages all settings, user preferences, and feature toggles
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)

# Paths
SETTINGS_DIR = Path("config")
SETTINGS_DIR.mkdir(exist_ok=True)
USER_PREFS_FILE = SETTINGS_DIR / "user_preferences.json"


class Settings:
    """Global settings and configuration"""
    
    def __init__(self):
        # API Keys (from environment)
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
        
        # Model settings
        self.DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "local")  # "local" or "api"
        self.OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "neural-chat")
        
        # Feature toggles
        self.ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
        self.ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"
        self.ENABLE_PDF_RAG = os.getenv("ENABLE_PDF_RAG", "true").lower() == "true"
        self.ENABLE_PHONE_ADB = os.getenv("ENABLE_PHONE_ADB", "true").lower() == "true"
        
        # Rate limiting
        self.GEMINI_RATE_LIMIT = int(os.getenv("GEMINI_RATE_LIMIT", "60"))
        self.WEB_SEARCH_RATE_LIMIT = int(os.getenv("WEB_SEARCH_RATE_LIMIT", "30"))
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "false").lower() == "true"
        
        # Defaults
        self.DEFAULT_TONE = "professional"
        self.NOTIFICATION_LEVEL = "info"  # debug, info, warning, error
        self.MEMORY_WINDOW = 15  # turns to remember


class UserPreferences:
    """Per-user preferences and settings"""
    
    @staticmethod
    def load_all() -> Dict[str, Dict[str, Any]]:
        """Load all user preferences from disk"""
        if USER_PREFS_FILE.exists():
            try:
                with open(USER_PREFS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user preferences: {e}")
                return {}
        return {}
    
    @staticmethod
    def save_all(prefs: Dict[str, Dict[str, Any]]):
        """Save all user preferences to disk"""
        try:
            with open(USER_PREFS_FILE, 'w') as f:
                json.dump(prefs, f, indent=2)
            logger.debug(f"Saved preferences for {len(prefs)} users")
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
    
    @staticmethod
    def get_user_prefs(user_id: str) -> Dict[str, Any]:
        """Get preferences for a specific user"""
        all_prefs = UserPreferences.load_all()
        
        if user_id not in all_prefs:
            # Create default preferences
            all_prefs[user_id] = UserPreferences.get_default_prefs(user_id)
            UserPreferences.save_all(all_prefs)
        
        return all_prefs[user_id]
    
    @staticmethod
    def set_user_pref(user_id: str, key: str, value: Any):
        """Set a specific preference for a user"""
        all_prefs = UserPreferences.load_all()
        
        if user_id not in all_prefs:
            all_prefs[user_id] = UserPreferences.get_default_prefs(user_id)
        
        all_prefs[user_id][key] = value
        UserPreferences.save_all(all_prefs)
        logger.debug(f"Updated {user_id} preference: {key} = {value}")
    
    @staticmethod
    def get_default_prefs(user_id: str) -> Dict[str, Any]:
        """Get default preferences for a new user"""
        return {
            "user_id": user_id,
            "preferred_model": "api",  # "api" or "local"
            "default_tone": "professional",  # "casual", "formal", "brief", "detailed", "funny"
            "language": "en",  # "en", "hi", "te", etc.
            "timezone": "Asia/Kolkata",
            "location": {
                "lat": 17.4,
                "lon": 78.6,
                "name": "Hyderabad"
            },
            "privacy_mode": False,  # Don't log inputs
            "auto_web_search": True,
            "enable_voice": True,
            "enable_pdf_rag": True,
            "notification_level": "info",  # debug, info, warning
            # ✅ NEW: Experiment 5 - Stylometric Defense
            "stealth_mode": False,  # Enable linguistic masking (defaults OFF - see DECISION_CARD_TEAM_MEETING.md)
            "created_at": str(datetime.now()),
            "last_active": str(datetime.now()),
        }
    
    @staticmethod
    def toggle_stealth_mode(user_id: str, enabled: bool):
        """Enable/disable Stealth Mode (linguistic masking) for a user"""
        UserPreferences.set_user_pref(user_id, "stealth_mode", enabled)
        status = "enabled" if enabled else "disabled"
        logger.info(f"Stealth Mode {status} for user {user_id}")


# Global settings instance
settings = Settings()


# Usage examples:
# from config.settings import settings, UserPreferences
#
# # Access global setting
# if settings.ENABLE_WEB_SEARCH:
#     result = web_search(query)
#
# # Access user preference
# user_prefs = UserPreferences.get_user_prefs(user_id)
# model = user_prefs["preferred_model"]
#
# # Update user preference
# UserPreferences.set_user_pref(user_id, "prefer_tone", "casual")
