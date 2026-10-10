"""End-to-end routing through core.orchestrator with every external call faked."""

from datetime import datetime, timedelta

import pytest

from core.handlers.base import STAGE_COMMAND, STAGE_FALLBACK
from core.orchestrator import generate_response, respond
from core.session import sessions
from models.errors import LLMError, QuotaExceededError


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr("core.handlers.email.send_email", lambda to, subj, body: sent.append((to, subj, body)) or f"Email sent to {to}.")
    return sent


# ── per-user isolation (the shared-global-state bug) ──────────────────────────

def test_other_user_cannot_confirm_pending_email(outbox, fake_llm):
    reply = respond("send email to boss@example.com saying I will be late to the review today", user_id="alice")
    assert "Confirm SEND" in reply.text

    respond("yes", user_id="mallory")
    assert outbox == []
    assert sessions.get("alice").email["pending"] is True

    respond("yes", user_id="alice")
    assert outbox == [("boss@example.com", "", "I will be late to the review today")]
    assert sessions.get("alice").email["pending"] is False


def test_tone_is_per_user():
    respond("set tone to funny", user_id="alice")
    assert sessions.get("alice").tone == "funny"
    assert sessions.get("bob").tone != "funny"


# ── email flow ───────────────────────────────────────────────────────────────

def test_cancel_email(outbox):
    respond("send email to a@b.com saying the report is attached and ready for review", user_id="u")
    assert "cancelled" in respond("no", user_id="u").text
    assert outbox == []


def test_regenerate_handles_braces_in_body(monkeypatch, outbox):
    # Old code called str.format() on text containing the body -> KeyError on "{".
    monkeypatch.setattr("core.handlers.email.generate_llm", lambda p, m="api": "Hi {team}, update: {status}")
    respond("send email to a@b.com use ai write about the sprint", user_id="u")
    reply = respond("regenerate make it shorter", user_id="u")
    assert "{team}" in reply.text
    assert "Feedback applied: make it shorter" in reply.text


def test_failed_generation_never_becomes_email_body(monkeypatch, outbox):
    def broken(prompt, model_type="api"):
        raise LLMError("quota exhausted")

    monkeypatch.setattr("core.handlers.email.generate_llm", broken)
    reply = respond("send email to a@b.com use ai write about the sprint", user_id="u")
    assert "could not answer" in reply.text
    assert sessions.get("u").email["pending"] is False


# ── calendar flow ────────────────────────────────────────────────────────────

def test_calendar_add_requires_confirmation(monkeypatch):
    added = []
    start = datetime.now() + timedelta(days=1)
    monkeypatch.setattr("core.handlers.calendar.parse_event_datetime", lambda text: start)
    monkeypatch.setattr("core.handlers.calendar.add_event", lambda **kw: added.append(kw) or "Event added.")

    reply = respond("add meeting with Ravi tomorrow at 3pm", user_id="u")
    assert "Add to Google Calendar?" in reply.text and added == []
    assert respond("yes", user_id="u").text == "Event added."
    assert added[0]["start"] == start


# ── privacy boundary and model errors ────────────────────────────────────────

def test_local_failure_does_not_go_to_cloud(monkeypatch):
    cloud_calls = []
    monkeypatch.setattr("core.model_manager._local", lambda p: (_ for _ in ()).throw(LLMError("ollama down")))
    monkeypatch.setattr("core.model_manager._gemini", lambda p: cloud_calls.append(p) or "cloud")

    reply = respond("explain quantum tunnelling", user_id="u", model_type="local")
    assert "NOT sent to the cloud" in reply.text
    assert cloud_calls == []


def test_local_mode_drafts_email_locally(fake_llm, outbox):
    # Experiment 4's guarantee: in local mode nothing is sent to the cloud.
    respond("send email to a@b.com use ai write about the sprint", user_id="u", model_type="local")
    respond("regenerate", user_id="u", model_type="local")
    assert fake_llm and all(model == "local" for model, _ in fake_llm)


def test_quota_falls_back_to_local(monkeypatch):
    from core import model_manager

    monkeypatch.setattr(model_manager, "_gemini", lambda p: (_ for _ in ()).throw(QuotaExceededError("429")))
    monkeypatch.setattr(model_manager, "_local", lambda p: "local answer")
    assert model_manager.generate_llm("hi", "api") == "local answer"


def test_unexpected_errors_become_a_reply(monkeypatch):
    def boom(req):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("core.orchestrator.PIPELINE", [boom])
    reply = respond("hello", user_id="u")
    assert "Something went wrong" in reply.text and reply.stage == STAGE_FALLBACK


# ── misc ─────────────────────────────────────────────────────────────────────

def test_help_is_a_command_stage():
    reply = respond("/help", user_id="u")
    assert reply.stage == STAGE_COMMAND and "Orchestrix" in reply.text


def test_turns_are_recorded(fake_llm):
    generate_response("what is 2+2", user_id="u", model_type="local")
    assert sessions.get("u").memory.recent()[-1]["user"] == "what is 2+2"


def test_reminders_need_telegram():
    assert "Telegram" in respond("remind me to stretch at 5pm", user_id="u").text


def test_location_command_saves_location():
    from tools.location_tool import get_user_location

    respond("/location:17.4:78.5:Home", user_id="u")
    assert get_user_location("u")["name"] == "Home"
