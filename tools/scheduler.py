"""
scheduler.py - Scheduled reminders and daily briefing
Install: pip install apscheduler
Add to .env: TELEGRAM_CHAT_ID=your_chat_id
             DAILY_BRIEFING_HOUR=8  (optional, default 8am)

Get your chat ID: message @userinfobot on Telegram
"""

import os
import json
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

REMINDERS_FILE = "data/reminders.json"
TIMEZONE       = "Asia/Kolkata"
os.makedirs("data", exist_ok=True)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)




def _load_reminders() -> list:
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_reminders(reminders: list):
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)




async def _send_telegram_message(bot, chat_id: str, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Scheduler send error: {e}")




def schedule_reminder(
    bot,
    chat_id: str,
    message: str,
    run_at: datetime,
    reminder_id: str = None,
) -> str:
    """
    Schedule a one-time reminder message.
    run_at: timezone-aware datetime
    """
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=ZoneInfo(TIMEZONE))

    now = datetime.now(ZoneInfo(TIMEZONE))
    if run_at <= now:
        return "Error: Reminder time is in the past."

    if reminder_id is None:
        reminder_id = f"reminder_{int(run_at.timestamp())}"

    async def send_it():
        await _send_telegram_message(bot, chat_id, f"Reminder: {message}")
        # Remove from saved reminders after firing
        reminders = _load_reminders()
        reminders = [r for r in reminders if r.get("id") != reminder_id]
        _save_reminders(reminders)

    scheduler.add_job(
        send_it,
        trigger=DateTrigger(run_date=run_at),
        id=reminder_id,
        replace_existing=True,
    )

    # Persist
    reminders = _load_reminders()
    reminders.append({
        "id":      reminder_id,
        "message": message,
        "run_at":  run_at.isoformat(),
        "chat_id": chat_id,
    })
    _save_reminders(reminders)

    time_str = run_at.strftime("%b %d at %I:%M %p")
    return f"Reminder set for {time_str}: {message}"


def list_reminders() -> str:
    reminders = _load_reminders()
    if not reminders:
        return "No reminders scheduled."

    lines = [f"Scheduled reminders ({len(reminders)}):"]
    for r in reminders:
        try:
            dt       = datetime.fromisoformat(r["run_at"])
            time_str = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            time_str = r.get("run_at", "unknown")
        lines.append(f"- {r['message']} at {time_str}")

    return "\n".join(lines)


def cancel_reminder(keyword: str) -> str:
    reminders = _load_reminders()
    matched   = [r for r in reminders if keyword.lower() in r["message"].lower()]

    if not matched:
        return f"No reminder found matching '{keyword}'."

    for r in matched:
        try:
            scheduler.remove_job(r["id"])
        except Exception:
            pass

    remaining = [r for r in reminders if r not in matched]
    _save_reminders(remaining)
    return f"Cancelled {len(matched)} reminder(s) matching '{keyword}'."




def setup_daily_briefing(bot, chat_id: str, generate_briefing_fn):
    """
    Sends a morning briefing every day at DAILY_BRIEFING_HOUR.
    generate_briefing_fn: async callable that returns briefing text
    """
    hour = int(os.getenv("DAILY_BRIEFING_HOUR", "8"))

    async def send_briefing():
        try:
            text = await generate_briefing_fn()
            await _send_telegram_message(bot, chat_id, text)
        except Exception as e:
            print(f"Daily briefing error: {e}")

    scheduler.add_job(
        send_briefing,
        trigger=CronTrigger(hour=hour, minute=0),
        id="daily_briefing",
        replace_existing=True,
    )
    print(f"Daily briefing scheduled at {hour}:00 {TIMEZONE}")




def restore_reminders(bot, chat_id: str):
    """
    Re-add any saved reminders that haven't fired yet.
    Call this when the bot starts.
    """
    reminders = _load_reminders()
    now       = datetime.now(ZoneInfo(TIMEZONE))
    kept      = []

    for r in reminders:
        try:
            run_at = datetime.fromisoformat(r["run_at"])
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=ZoneInfo(TIMEZONE))

            if run_at <= now:
                # Missed — skip
                continue

            async def send_it(msg=r["message"], rid=r["id"], cid=r.get("chat_id", chat_id)):
                await _send_telegram_message(bot, cid, f"Reminder: {msg}")
                saved    = _load_reminders()
                saved    = [x for x in saved if x.get("id") != rid]
                _save_reminders(saved)

            scheduler.add_job(
                send_it,
                trigger=DateTrigger(run_date=run_at),
                id=r["id"],
                replace_existing=True,
            )
            kept.append(r)

        except Exception as e:
            print(f"Could not restore reminder: {e}")

    _save_reminders(kept)
    if kept:
        print(f"Restored {len(kept)} reminder(s).")


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started.")