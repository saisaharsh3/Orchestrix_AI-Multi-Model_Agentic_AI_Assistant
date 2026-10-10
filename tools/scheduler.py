"""
scheduler.py - Scheduled reminders and the daily briefing (Telegram).

Reminders are stored in SQLite (namespace "reminders") and scoped to the
chat that created them. Set TELEGRAM_CHAT_ID for the daily briefing and
DAILY_BRIEFING_HOUR to change its time (default 8).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config.settings import settings
from core.logger import get_logger
from core.storage import get_store

logger = get_logger(__name__)

NAMESPACE = "reminders"
TZ = ZoneInfo(settings.TIMEZONE)

scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)


def _reminders(chat_id: str | None = None) -> list[dict]:
    items = [value for _, value in get_store().items(NAMESPACE)]
    if chat_id is not None:
        items = [r for r in items if str(r.get("chat_id")) == str(chat_id)]
    return sorted(items, key=lambda r: r.get("run_at", ""))


async def _send_telegram_message(bot, chat_id: str, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Scheduler could not send message to {chat_id}: {e}")


def _add_job(bot, reminder: dict, run_at: datetime) -> None:
    async def send_it():
        await _send_telegram_message(bot, reminder["chat_id"], f"Reminder: {reminder['message']}")
        get_store().delete(NAMESPACE, reminder["id"])

    scheduler.add_job(
        send_it,
        trigger=DateTrigger(run_date=run_at),
        id=reminder["id"],
        replace_existing=True,
    )


def schedule_reminder(bot, chat_id: str, message: str, run_at: datetime) -> str:
    """Schedule a one-time reminder. Naive datetimes are treated as TIMEZONE."""
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=TZ)
    if run_at <= datetime.now(TZ):
        return "Error: Reminder time is in the past."

    reminder = {
        "id": f"reminder_{chat_id}_{int(run_at.timestamp())}",
        "message": message,
        "run_at": run_at.isoformat(),
        "chat_id": str(chat_id),
    }
    _add_job(bot, reminder, run_at)
    get_store().put(NAMESPACE, reminder["id"], reminder)
    return f"Reminder set for {run_at.strftime('%b %d at %I:%M %p')}: {message}"


def list_reminders(chat_id: str | None = None) -> str:
    reminders = _reminders(chat_id)
    if not reminders:
        return "No reminders scheduled."
    lines = [f"Scheduled reminders ({len(reminders)}):"]
    for r in reminders:
        try:
            time_str = datetime.fromisoformat(r["run_at"]).strftime("%b %d, %I:%M %p")
        except (KeyError, ValueError):
            time_str = r.get("run_at", "unknown")
        lines.append(f"- {r['message']} at {time_str}")
    return "\n".join(lines)


def cancel_reminder(keyword: str, chat_id: str | None = None) -> str:
    matched = [r for r in _reminders(chat_id) if keyword.lower() in r["message"].lower()]
    if not matched:
        return f"No reminder found matching '{keyword}'."
    for r in matched:
        try:
            scheduler.remove_job(r["id"])
        except Exception:
            pass  # job already fired or was never scheduled in this process
        get_store().delete(NAMESPACE, r["id"])
    return f"Cancelled {len(matched)} reminder(s) matching '{keyword}'."


def setup_daily_briefing(bot, chat_id: str, generate_briefing_fn) -> None:
    """Send `await generate_briefing_fn()` to chat_id every day at DAILY_BRIEFING_HOUR."""
    hour = settings.DAILY_BRIEFING_HOUR

    async def send_briefing():
        try:
            text = await generate_briefing_fn()
            await _send_telegram_message(bot, chat_id, text)
        except Exception as e:
            logger.error(f"Daily briefing failed: {e}", exc_info=True)

    scheduler.add_job(
        send_briefing,
        trigger=CronTrigger(hour=hour, minute=0),
        id="daily_briefing",
        replace_existing=True,
    )
    logger.info(f"Daily briefing scheduled at {hour}:00 {settings.TIMEZONE}")


def restore_reminders(bot) -> None:
    """Re-schedule saved reminders that have not fired yet; drop missed ones."""
    now = datetime.now(TZ)
    restored = 0
    for r in _reminders():
        try:
            run_at = datetime.fromisoformat(r["run_at"])
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=TZ)
            if run_at <= now:
                get_store().delete(NAMESPACE, r["id"])
                continue
            _add_job(bot, r, run_at)
            restored += 1
        except (KeyError, ValueError) as e:
            logger.warning(f"Could not restore reminder {r.get('id')}: {e}")
    if restored:
        logger.info(f"Restored {restored} reminder(s)")


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
