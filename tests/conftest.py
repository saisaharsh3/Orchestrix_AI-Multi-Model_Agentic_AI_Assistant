import os
import sys
import tempfile
from pathlib import Path

# Configure the environment before any project module reads it.
_TMP = Path(tempfile.mkdtemp(prefix="orchestrix-tests-"))
os.environ.update(
    {
        "ORCHESTRIX_DATA_DIR": str(_TMP / "data"),
        "LOG_DIR": str(_TMP / "logs"),
        # Empty folder: tests must never reach a real Google account.
        "GOOGLE_CREDENTIALS_DIR": str(_TMP / "no-credentials"),
        "LOG_LEVEL": "WARNING",
        "ENABLE_RESEARCH_TRACE": "false",
        "ENABLE_LLM_TOOL_ROUTING": "false",
        "GEMINI_API_KEY": "",
        "TELEGRAM_ALLOWED_USER_IDS": "111",
        "TELEGRAM_ALLOW_ALL": "false",
        "ORCHESTRIX_API_TOKEN": "",
        "DEFAULT_MODEL": "local",
        "ENABLE_WEB_SEARCH": "false",
    }
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from core import storage  # noqa: E402
from core.session import sessions  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test gets an empty in-memory database and no cached sessions."""
    store = storage.Store(":memory:")
    storage.set_store(store)
    sessions.clear()
    yield store
    sessions.clear()
    storage.set_store(None)
    store.close()


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace every model call with a canned answer; records prompts."""
    calls = []

    def generate(prompt, model_type="api"):
        calls.append((model_type, prompt))
        return f"LLM[{model_type}]"

    for module in ("core.model_manager", "core.handlers.email", "core.handlers.knowledge",
                   "core.handlers.features", "core.handlers.utilities"):
        monkeypatch.setattr(f"{module}.generate_llm", generate, raising=False)
    return calls
