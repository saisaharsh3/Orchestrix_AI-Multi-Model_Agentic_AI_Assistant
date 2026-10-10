import json

from core import storage
from core.conversation_memory import ConversationMemory


def test_kv_roundtrip(fresh_state):
    fresh_state.put("ns", "k", {"a": 1})
    assert fresh_state.get("ns", "k") == {"a": 1}
    assert fresh_state.get("ns", "missing", "default") == "default"
    assert fresh_state.delete("ns", "k")
    assert fresh_state.get("ns", "k") is None


def test_items_are_namespaced(fresh_state):
    fresh_state.put("a", "1", 1)
    fresh_state.put("b", "1", 2)
    assert list(fresh_state.items("a")) == [("1", 1)]


def test_conversation_memory_is_per_user():
    alice, bob = ConversationMemory("alice"), ConversationMemory("bob")
    alice.add_turn("my secret is blue", "noted")
    bob.add_turn("hello", "hi")
    assert [t["user"] for t in alice.recent()] == ["my secret is blue"]
    assert "No past messages" in bob.search_history("secret")
    assert "my secret is blue" in alice.search_history("secret")


def test_recent_turns_are_oldest_first_and_limited():
    mem = ConversationMemory("u")
    for i in range(5):
        mem.add_turn(f"msg {i}", "ok")
    assert [t["user"] for t in mem.recent(3)] == ["msg 2", "msg 3", "msg 4"]


def test_email_context_returns_most_recent_recipient_first():
    mem = ConversationMemory("u")
    mem.add_turn("email old@example.com", "ok")
    mem.add_turn("email new@example.com", "ok")
    assert mem.get_feature_context("email")["recent_recipients"][0] == "new@example.com"


def test_legacy_json_is_imported_once(tmp_path, monkeypatch):
    prefs = tmp_path / "prefs.json"
    prefs.write_text(json.dumps({"42": {"preferred_model": "api"}}))
    reminders = tmp_path / "reminders.json"
    reminders.write_text(json.dumps([{"id": "r1", "message": "x", "chat_id": "42"}]))
    monkeypatch.setattr(storage, "_LEGACY_FILES", {"user_prefs": prefs, "reminders": reminders})

    store = storage.Store(":memory:")
    storage._migrate_legacy_json(store)
    assert store.get("user_prefs", "42") == {"preferred_model": "api"}
    assert store.get("reminders", "r1")["message"] == "x"

    prefs.write_text(json.dumps({"42": {"preferred_model": "local"}}))
    storage._migrate_legacy_json(store)  # second run is a no-op
    assert store.get("user_prefs", "42") == {"preferred_model": "api"}
