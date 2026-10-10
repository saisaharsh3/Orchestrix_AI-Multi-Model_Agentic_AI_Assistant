"""
core/agent/tools.py - The tool registry shared by the agent, Gemini tool
routing and the MCP server.

Every tool declares a standard JSON Schema for its arguments and a kind:
  READ  – no side effects; may run automatically
  WRITE – changes something (sends, creates, controls a device); only runs
          after the user explicitly confirms
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from config.settings import settings

READ = "read"
WRITE = "write"

MAX_RESULT_CHARS = 2000


@dataclass
class ToolContext:
    """What a tool may need about the caller."""
    user_id: str
    session: Any = None  # core.session.Session, when available


@dataclass
class Tool:
    name: str
    description: str
    kind: str
    run: Callable[..., str]
    properties: dict = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    @property
    def schema(self) -> dict:
        schema: dict = {"type": "object", "properties": self.properties}
        if self.required:
            schema["required"] = self.required
        return schema

    def gemini_declaration(self) -> dict:
        decl = {"name": self.name, "description": self.description}
        # Gemini rejects OBJECT schemas with no properties; omit them instead.
        if self.properties:
            decl["parameters"] = self.schema
        return decl

    def describe(self, args: dict) -> str:
        shown = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
        return f"{self.name}({shown})"

    def execute(self, ctx: ToolContext, args: dict) -> str:
        unknown = set(args) - set(self.properties)
        if unknown:
            raise ValueError(f"unknown argument(s) for {self.name}: {', '.join(sorted(unknown))}")
        missing = [r for r in self.required if r not in args]
        if missing:
            raise ValueError(f"missing argument(s) for {self.name}: {', '.join(missing)}")
        result = self.run(ctx, **args)
        result = result if isinstance(result, str) else str(result)
        if len(result) > MAX_RESULT_CHARS:
            result = result[:MAX_RESULT_CHARS] + " …[truncated]"
        return result


def _short(value: Any, limit: int = 60) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}


def _desc(schema: dict, description: str) -> dict:
    return {**schema, "description": description}


# ── READ tools ────────────────────────────────────────────────────────────────

def _weather(ctx, city: str = "") -> str:
    from tools.weather_tool import get_weather
    return get_weather(city or settings.DEFAULT_CITY)


def _forecast(ctx, city: str = "", days: int = 3) -> str:
    from tools.weather_tool import get_forecast
    return get_forecast(city or settings.DEFAULT_CITY, days=max(1, min(int(days), 5)))


def _convert(ctx, amount: float, from_currency: str, to_currency: str) -> str:
    from tools.finance_tool import convert_currency
    return convert_currency(float(amount), from_currency.upper(), to_currency.upper())


def _stock(ctx, ticker: str) -> str:
    from tools.finance_tool import get_stock_price
    return get_stock_price(ticker.upper())


def _crypto(ctx, symbol: str) -> str:
    from tools.finance_tool import get_crypto_price
    return get_crypto_price(symbol.upper())


def _list_tasks(ctx) -> str:
    from tools.google_tasks_tool import list_tasks
    return list_tasks()


def _events(ctx, days_ahead: int = 7) -> str:
    from tools.calendar_tool import list_events
    return list_events(days_ahead=max(1, min(int(days_ahead), 31)))


def _inbox(ctx) -> str:
    from tools.email_tool import format_inbox, read_inbox
    return format_inbox(read_inbox(max_results=5, unread_only=True))


def _search_email(ctx, query: str) -> str:
    from tools.email_tool import search_emails
    return search_emails(query)


def _drive(ctx, query: str) -> str:
    from tools.google_drive_tool import search_drive
    return search_drive(query)


def _web(ctx, query: str) -> str:
    from tools.web_search import web_search
    results = web_search(query, max_results=5)
    return "\n\n".join(results) if results else "No web results."


def _wiki(ctx, topic: str) -> str:
    from tools.wiki_search import wiki_search
    return wiki_search(topic) or f"No Wikipedia article found for '{topic}'."


def _read_webpage(ctx, url: str) -> str:
    from tools.url_tool import fetch_url_text
    title, text = fetch_url_text(url, max_chars=MAX_RESULT_CHARS)
    return text if text.startswith("Error") else f"{title}\n\n{text}"


def _search_docs(ctx, query: str) -> str:
    session = ctx.session
    if session is None:
        from core.session import sessions
        session = sessions.get(ctx.user_id)
    if not session.has_documents:  # avoid loading the embedding model for nothing
        return "No documents are indexed yet. Upload a PDF first."
    store = session.pdf_store
    hits = store.smart_search(query, top_k=5)
    return "\n\n".join(f"[{i}] {chunk[:400]}" for i, chunk in enumerate(hits, 1)) or "No matching passages."


def _recall(ctx, query: str) -> str:
    from core.conversation_memory import ConversationMemory
    return ConversationMemory(ctx.user_id).search_history(query)


def _tracked_prices(ctx) -> str:
    from tools.url_tool import show_tracked_prices
    return show_tracked_prices(user_id=ctx.user_id)


def _now(ctx) -> str:
    now = datetime.now(ZoneInfo(settings.TIMEZONE))
    return now.strftime(f"%A %Y-%m-%d %H:%M ({settings.TIMEZONE})")


# ── WRITE tools (run only after confirmation) ─────────────────────────────────

def _add_task(ctx, title: str, due_date: str = "") -> str:
    from tools.google_tasks_tool import add_task
    return add_task(title, due=due_date)


def _create_event(ctx, title: str, start: str, duration_minutes: int = 60, location: str = "") -> str:
    from tools.calendar_tool import add_event
    start_dt = datetime.fromisoformat(start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=ZoneInfo(settings.TIMEZONE))
    end_dt = start_dt + timedelta(minutes=int(duration_minutes))
    return add_event(title=title, start=start_dt, end=end_dt, location=location)


def _send_email(ctx, to: str, subject: str, body: str) -> str:
    from tools.email_tool import send_email
    return send_email(to, subject, body)


def _draft_email(ctx, to: str, subject: str, body: str) -> str:
    from tools.email_tool import save_draft
    return save_draft(to, subject, body)


def _set_alarm(ctx, hour: int, minute: int = 0) -> str:
    from tools.web_automation.phone_actions import set_alarm
    return set_alarm(int(hour), int(minute))


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("get_current_time", "Current date and time in the user's timezone.", READ, _now),
        Tool("get_weather", "Current weather for a city.", READ, _weather, {"city": _STR}),
        Tool("get_forecast", "Weather forecast for the next 1-5 days.", READ, _forecast,
             {"city": _STR, "days": _INT}),
        Tool("convert_currency", "Convert an amount between currencies (ISO codes like USD, INR).", READ, _convert,
             {"amount": _NUM, "from_currency": _STR, "to_currency": _STR},
             ["amount", "from_currency", "to_currency"]),
        Tool("get_stock_price", "Latest stock price for a ticker (e.g. TCS.NS, AAPL).", READ, _stock,
             {"ticker": _STR}, ["ticker"]),
        Tool("get_crypto_price", "Latest price of a cryptocurrency (e.g. BTC, ETH).", READ, _crypto,
             {"symbol": _STR}, ["symbol"]),
        Tool("list_tasks", "The user's pending Google Tasks.", READ, _list_tasks),
        Tool("list_calendar_events", "The user's upcoming Google Calendar events.", READ, _events,
             {"days_ahead": _INT}),
        Tool("check_inbox", "The user's unread Gmail messages.", READ, _inbox),
        Tool("search_email", "Search the user's Gmail (Gmail search syntax works).", READ, _search_email,
             {"query": _STR}, ["query"]),
        Tool("search_drive", "Search the user's Google Drive files by name.", READ, _drive,
             {"query": _STR}, ["query"]),
        Tool("web_search", "Search the web (DuckDuckGo).", READ, _web, {"query": _STR}, ["query"]),
        Tool("wikipedia", "Wikipedia summary of a topic.", READ, _wiki, {"topic": _STR}, ["topic"]),
        Tool("read_webpage", "Fetch the readable text of a public web page.", READ, _read_webpage,
             {"url": _STR}, ["url"]),
        Tool("search_my_documents",
             "Search the user's uploaded PDFs (local, on-device index). Returns matching passages.",
             READ, _search_docs, {"query": _STR}, ["query"]),
        Tool("recall_conversation", "Search earlier messages in this user's conversation history.", READ, _recall,
             {"query": _STR}, ["query"]),
        Tool("get_tracked_prices", "Products the user is tracking and their latest prices.", READ, _tracked_prices),

        Tool("add_task", "Add a Google Task.", WRITE, _add_task,
             {"title": _STR, "due_date": _desc(_STR, "YYYY-MM-DD, optional")}, ["title"]),
        Tool("create_calendar_event", "Create a Google Calendar event.", WRITE, _create_event,
             {"title": _STR,
              "start": _desc(_STR, "ISO 8601 local date-time, e.g. 2026-10-11T10:00"),
              "duration_minutes": _INT,
              "location": _STR},
             ["title", "start"]),
        Tool("send_email", "Send an email from the user's Gmail.", WRITE, _send_email,
             {"to": _STR, "subject": _STR, "body": _STR}, ["to", "subject", "body"]),
        Tool("save_email_draft", "Save an email as a Gmail draft without sending.", WRITE, _draft_email,
             {"to": _STR, "subject": _STR, "body": _STR}, ["to", "subject", "body"]),
        Tool("set_phone_alarm", "Set an alarm on the user's Android phone (24-hour time).", WRITE, _set_alarm,
             {"hour": _INT, "minute": _INT}, ["hour"]),
    ]
}


def tools_of(kind: str | None = None) -> list[Tool]:
    return [t for t in TOOLS.values() if kind is None or t.kind == kind]
