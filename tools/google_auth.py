"""
google_auth.py - Shared OAuth for Gmail, Calendar, Tasks and Drive.

One token (credentials/token.json) covers all four APIs. The first run opens
a browser for consent; after that the token is refreshed automatically.
"""

import threading

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import settings
from core.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_PATH = settings.CREDENTIALS_DIR / "credentials.json"
TOKEN_PATH = settings.CREDENTIALS_DIR / "token.json"

_lock = threading.Lock()
_creds: Credentials | None = None


def get_credentials() -> Credentials:
    global _creds
    with _lock:
        creds = _creds
        if creds is None and TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            _creds = creds
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                # Revoked or expired for good (e.g. "invalid_grant"): ask for consent again.
                logger.warning(f"Google token refresh failed ({e}); re-running consent flow")
                creds = None
        else:
            creds = None

        if creds is None:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Google OAuth client file not found at {CREDENTIALS_PATH}. "
                    "See README > Google APIs setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        _creds = creds
        return creds


def get_service(api: str, version: str):
    """e.g. get_service("gmail", "v1"), get_service("calendar", "v3")."""
    return build(api, version, credentials=get_credentials(), cache_discovery=False)
