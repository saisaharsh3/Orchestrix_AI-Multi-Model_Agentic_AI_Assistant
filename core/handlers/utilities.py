"""Weather, finance, URLs, Drive, reminders and PDF compare/report."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import settings
from core.handlers.base import Reply, Request
from core.model_manager import generate_llm
from tools.utility_intent import detect_utility_intent


def parse_reminder_time(time_str: str, day: str = "today", now: datetime | None = None) -> datetime | None:
    """'6pm' / '6:30 am' + 'today'|'tomorrow' -> aware datetime (rolls to tomorrow if past)."""
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", time_str.lower())
    if not m:
        return None
    hour, minute, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if not (1 <= hour <= 12 and 0 <= minute < 60):
        return None
    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    now = now or datetime.now(ZoneInfo(settings.TIMEZONE))
    base = now + timedelta(days=1) if day == "tomorrow" else now
    dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if day == "today" and dt <= now:
        dt += timedelta(days=1)
    return dt


def handle(req: Request) -> Reply | None:
    intent = detect_utility_intent(req.text)
    if not intent:
        return None
    kind = intent["type"]

    if kind in {"weather_current", "weather_forecast"}:
        from tools.weather_tool import get_forecast, get_weather
        city = intent.get("city") or settings.DEFAULT_CITY
        return Reply(get_forecast(city, days=3) if kind == "weather_forecast" else get_weather(city))

    if kind == "currency_convert":
        from tools.finance_tool import convert_currency
        return Reply(convert_currency(intent["amount"], intent["from_curr"], intent["to_curr"]))

    if kind == "stock_price":
        from tools.finance_tool import get_stock_price
        return Reply(get_stock_price(intent["ticker"]))

    if kind == "crypto_price":
        from tools.finance_tool import get_crypto_price
        return Reply(get_crypto_price(intent["symbol"]))

    if kind == "summarize_url":
        from tools.url_tool import summarize_url
        return Reply(summarize_url(intent["url"], generate_llm, req.model_type))

    if kind == "track_price":
        from tools.url_tool import track_price
        return Reply(track_price(intent["url"], user_id=req.user_id))

    if kind == "show_tracked_prices":
        from tools.url_tool import show_tracked_prices
        return Reply(show_tracked_prices(user_id=req.user_id))

    if kind in {"drive_search", "drive_recent", "drive_shared"}:
        from tools import google_drive_tool as drive
        if kind == "drive_search":
            return Reply(drive.search_drive(intent["query"]))
        if kind == "drive_recent":
            return Reply(drive.list_recent_files())
        return Reply(drive.list_shared_files())

    if kind.startswith("reminder_"):
        return _reminders(req, intent)

    if kind == "pdf_compare":
        pdfs = req.session.recent_pdfs
        if len(pdfs) < 2:
            return Reply("Please upload two PDFs first, then say 'compare the two PDFs'.")
        from tools.pdf_compare_tool import compare_pdfs
        return Reply(compare_pdfs(pdfs[-2], pdfs[-1], generate_llm, req.model_type))

    if kind == "pdf_report":
        if not req.session.recent_pdfs:
            return Reply("No PDF loaded. Send a PDF first.")
        from tools.pdf_compare_tool import summarize_pdf_to_report
        output = summarize_pdf_to_report(req.session.recent_pdfs[-1], generate_llm, req.model_type)
        if output.startswith("Error"):
            return Reply(output)
        return Reply("Here is your summary report.", files=[output])

    return None


def _reminders(req: Request, intent: dict) -> Reply:
    from tools.scheduler import cancel_reminder, list_reminders, schedule_reminder

    target = req.reminder_target
    if target is None:
        return Reply("Reminders are delivered through the Telegram bot. Run telegram_bot.py to use them.")

    if intent["type"] == "reminder_list":
        return Reply(list_reminders(target.chat_id))
    if intent["type"] == "reminder_cancel":
        return Reply(cancel_reminder(intent["keyword"], target.chat_id))

    run_at = parse_reminder_time(intent["time"], intent.get("day", "today"))
    if run_at is None:
        return Reply("Could not parse the reminder time. Try: remind me to call mom at 6pm")
    return Reply(schedule_reminder(target.bot, target.chat_id, intent["message"], run_at))
