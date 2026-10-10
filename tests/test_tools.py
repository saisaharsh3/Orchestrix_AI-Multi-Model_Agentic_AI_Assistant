"""Reminder time parsing, scheduler scoping, tool router and price tracking."""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.handlers.utilities import parse_reminder_time

TZ = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 10, 14, 0, tzinfo=TZ)


def test_reminder_later_today():
    assert parse_reminder_time("6pm", "today", now=NOW) == NOW.replace(hour=18)


def test_reminder_in_the_past_rolls_to_tomorrow():
    assert parse_reminder_time("9am", "today", now=NOW).day == 11


def test_reminder_tomorrow_and_edge_hours():
    assert parse_reminder_time("12:30 am", "tomorrow", now=NOW) == datetime(2026, 10, 11, 0, 30, tzinfo=TZ)
    assert parse_reminder_time("12 pm", "tomorrow", now=NOW).hour == 12


def test_reminder_invalid():
    assert parse_reminder_time("25pm", now=NOW) is None
    assert parse_reminder_time("soon", now=NOW) is None


def test_reminders_are_scoped_to_chat(fresh_state):
    from tools import scheduler

    fresh_state.put("reminders", "r1", {"id": "r1", "message": "pay rent", "run_at": "2099-01-01T09:00:00+05:30", "chat_id": "1"})
    fresh_state.put("reminders", "r2", {"id": "r2", "message": "pay fees", "run_at": "2099-01-01T09:00:00+05:30", "chat_id": "2"})
    assert "pay rent" in scheduler.list_reminders("1") and "pay fees" not in scheduler.list_reminders("1")
    assert scheduler.cancel_reminder("pay", chat_id="1").startswith("Cancelled 1")
    assert fresh_state.get("reminders", "r2") is not None


def test_empty_tool_schemas_are_omitted_for_gemini():
    from core.agent.tools import TOOLS

    decl = TOOLS["list_tasks"].gemini_declaration()
    assert "parameters" not in decl  # Gemini rejects empty OBJECT schemas


def test_tool_router_runs_chosen_tool(monkeypatch):
    from core import tool_router
    from core.agent.tools import READ, TOOLS, Tool

    monkeypatch.setattr("models.gemini_llm.gemini_generate_or_call", lambda p, d: ("call", ("get_weather", {"city": "Pune"})))
    monkeypatch.setitem(TOOLS, "get_weather", Tool("get_weather", "", READ, lambda ctx, city="": f"sunny in {city}", {"city": {"type": "string"}}))
    assert tool_router.route_or_answer("is it hot in pune") == ("sunny in Pune", "get_weather")


def test_tool_router_only_offers_read_tools(monkeypatch):
    from core import tool_router

    offered = []
    monkeypatch.setattr("models.gemini_llm.gemini_generate_or_call", lambda p, d: offered.extend(d) or ("text", "hi"))
    tool_router.route_or_answer("hello")
    assert "send_email" not in {d["name"] for d in offered}


def test_tool_router_ignores_unknown_tool(monkeypatch):
    from core import tool_router

    monkeypatch.setattr("models.gemini_llm.gemini_generate_or_call", lambda p, d: ("call", ("send_email", {})))
    assert tool_router.route_or_answer("x") == ("", None)


def test_tracked_prices_are_per_user(monkeypatch):
    from bs4 import BeautifulSoup

    from tools import url_tool

    page = BeautifulSoup('<title>Widget</title><span class="price">₹1,299</span>', "html.parser")
    monkeypatch.setattr(url_tool, "_fetch_page", lambda url: page)
    url_tool.track_price("https://shop.example/widget", user_id="alice")
    assert "Widget" in url_tool.show_tracked_prices("alice")
    assert "No products" in url_tool.show_tracked_prices("bob")
