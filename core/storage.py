"""
core/storage.py - SQLite persistence for user data.

Replaces the scattered JSON files (preferences, locations, reminders, tracked
prices, conversation history). SQLite gives atomic writes, so a crash or two
concurrent writers can no longer corrupt the data.

Two primitives:
    * key/value documents grouped by namespace  (get / put / delete / items)
    * an append-only conversation log per user  (add_turn / recent_turns)
"""

import json
import sqlite3
import threading
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    namespace  TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (namespace, key)
);
CREATE TABLE IF NOT EXISTS conversation_turns (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   TEXT NOT NULL,
    ts        TEXT NOT NULL,
    user_text TEXT NOT NULL,
    assistant TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_turns_user ON conversation_turns (user_id, id);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── key/value ──────────────────────────────────────────────────────────
    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE namespace = ? AND key = ?", (namespace, key)
            ).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, namespace: str, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO kv (namespace, key, value, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (namespace, key, json.dumps(value), datetime.now().isoformat()),
            )

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM kv WHERE namespace = ? AND key = ?", (namespace, key)
            )
        return cur.rowcount > 0

    def items(self, namespace: str) -> Iterator[tuple[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM kv WHERE namespace = ? ORDER BY key", (namespace,)
            ).fetchall()
        for key, value in rows:
            yield key, json.loads(value)

    # ── conversation log ───────────────────────────────────────────────────
    def add_turn(self, user_id: str, user_text: str, assistant: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO conversation_turns (user_id, ts, user_text, assistant) "
                "VALUES (?, ?, ?, ?)",
                (user_id, datetime.now().isoformat(), user_text, assistant),
            )

    def recent_turns(self, user_id: str, limit: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, user_text, assistant FROM conversation_turns "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [
            {"timestamp": ts, "user": u, "assistant": a} for ts, u, a in reversed(rows)
        ]

    def search_turns(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        pattern = f"%{query}%"
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, user_text, assistant FROM conversation_turns "
                "WHERE user_id = ? AND (user_text LIKE ? OR assistant LIKE ?) "
                "ORDER BY id DESC LIMIT ?",
                (user_id, pattern, pattern, limit),
            ).fetchall()
        return [{"timestamp": ts, "user": u, "assistant": a} for ts, u, a in rows]

    def count_turns(self, user_id: str) -> int:
        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM conversation_turns WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_store: Store | None = None
_store_lock = threading.Lock()


def get_store() -> Store:
    """Return the process-wide store, creating it (and migrating old JSON) on first use."""
    global _store
    with _store_lock:
        if _store is None:
            _store = Store(settings.DB_PATH)
            _migrate_legacy_json(_store)
        return _store


def set_store(store: Store | None) -> None:
    """Swap the global store (used by tests)."""
    global _store
    with _store_lock:
        _store = store


# ── one-time import of the old JSON files ─────────────────────────────────────

_LEGACY_FILES = {
    "user_prefs": Path("config/user_preferences.json"),
    "user_locations": Path("data/user_locations.json"),
    "tracked_prices": Path("data/tracked_prices.json"),
    "reminders": Path("data/reminders.json"),
}


def _migrate_legacy_json(store: Store) -> None:
    for namespace, path in _LEGACY_FILES.items():
        if not path.exists() or store.get("_migrations", namespace):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "null")
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Skipping legacy file {path}: {e}")
            continue

        if isinstance(data, dict):
            for key, value in data.items():
                if namespace == "tracked_prices":
                    # Old file was global; give the items to the bot owner.
                    owner = settings.TELEGRAM_CHAT_ID or "local"
                    key = f"{owner}|{str(key)[:100]}"
                store.put(namespace, str(key), value)
        elif isinstance(data, list):  # reminders: list of dicts with an "id"
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    store.put(namespace, item["id"], item)

        store.put("_migrations", namespace, datetime.now().isoformat())
        logger.info(f"Imported legacy {path} into SQLite namespace '{namespace}'")
