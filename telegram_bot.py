"""
telegram_bot.py - Telegram front end for Orchestrix.

Only users listed in TELEGRAM_ALLOWED_USER_IDS (or TELEGRAM_CHAT_ID) can use
the bot: it has access to your Gmail, Calendar, Drive and phone.
"""

import asyncio
import functools
import os
import tempfile
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import UserPreferences, settings
from core.handlers import ReminderTarget
from core.logger import get_logger
from core.orchestrator import respond
from core.session import sessions
from tools.scheduler import list_reminders, restore_reminders, setup_daily_briefing, start_scheduler

logger = get_logger(__name__)

MAX_LEN = 4096  # Telegram message limit

try:
    from tools.voice_tool import transcribe_audio
    VOICE_AVAILABLE = settings.ENABLE_VOICE
except ImportError:
    VOICE_AVAILABLE = False


# ── access control ────────────────────────────────────────────────────────────

def is_allowed(user_id: int | str | None) -> bool:
    if settings.TELEGRAM_ALLOW_ALL:
        return True
    return user_id is not None and str(user_id) in settings.TELEGRAM_ALLOWED_USER_IDS


def restricted(handler):
    """Drop updates from anyone not on the allowlist."""
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not is_allowed(user.id if user else None):
            logger.warning(f"Blocked message from unauthorised user {user.id if user else '?'}")
            if update.message:
                await update.message.reply_text(
                    f"Sorry, this is a private assistant. Your user id is {user.id if user else '?'}."
                )
            return
        return await handler(update, context)
    return wrapper


# ── helpers ───────────────────────────────────────────────────────────────────

def _session(update: Update):
    return sessions.get(str(update.effective_user.id))


def status_text(update: Update) -> str:
    s = _session(update)
    store = s._pdf_store
    files = ", ".join(sorted(store.loaded_files)) if store and store.loaded_files else "none"
    chunks = len(store.text_chunks) if store else 0
    return (
        f"\n\nSystem Status\n"
        f"Model  : {s.model_type.upper()}\n"
        f"Web    : {'ON' if s.use_web else 'OFF'}\n"
        f"RAG    : {'ON' if s.use_pdf else 'OFF'}\n"
        f"Chunks : {chunks}\n"
        f"PDFs   : {files}"
    )


async def _send(update: Update, text: str) -> None:
    for i in range(0, len(text), MAX_LEN):
        await update.message.reply_text(text[i:i + MAX_LEN])


async def _answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Run the (blocking) orchestrator in a worker thread and send the reply."""
    thinking = await update.message.reply_text("Thinking...")
    target = ReminderTarget(bot=context.application.bot, chat_id=str(update.effective_chat.id))
    reply = await asyncio.to_thread(
        respond, text, user_id=str(update.effective_user.id), reminder_target=target
    )

    first, rest = reply.text[:MAX_LEN], reply.text[MAX_LEN:]
    try:
        await thinking.edit_text(first or "(empty response)")
    except Exception:
        await update.message.reply_text(first or "(empty response)")
    if rest:
        await _send(update, rest)

    for path in reply.files:
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(path))


# ── commands ──────────────────────────────────────────────────────────────────

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Orchestrix AI Connected!\n\n"
        "Commands:\n"
        "/api /local - switch model\n"
        "/web on|off - toggle web search\n"
        "/rag on|off - toggle PDF mode\n"
        "/clearpdf   - clear PDFs\n"
        "/status     - current settings\n"
        "/reminders  - list reminders\n"
        "/stealth_mode on|off - stylometric masking for cloud queries\n"
        "/share_location - share your location for maps\n\n"
        "What you can say:\n"
        "- weather in Mumbai\n"
        "- convert 500 USD to INR\n"
        "- TCS stock price\n"
        "- add task buy milk / show my tasks\n"
        "- find resume on drive\n"
        "- remind me to call mom at 6pm\n"
        "- summarize https://...\n"
        "- track price https://...\n"
        "- find restaurants nearby / directions to airport\n"
        "- compare the two PDFs\n"
        "- open youtube / set alarm for 7am\n\n"
        "Send a voice message to transcribe it.\n"
        "Send a PDF to index it for Q&A.\n"
        "Send a location pin to use maps features."
    )


@restricted
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Current status:" + status_text(update))


async def _set_model(update: Update, model: str) -> None:
    session = _session(update)
    session.model_type = model
    UserPreferences.set_user_pref(session.user_id, "preferred_model", model)
    label = "API model (Gemini)" if model == "api" else "LOCAL model"
    await update.message.reply_text(f"Switched to {label}" + status_text(update))


@restricted
async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_model(update, "api")


@restricted
async def set_local(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_model(update, "local")


def _on_off(context) -> bool | None:
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        return None
    return context.args[0].lower() == "on"


@restricted
async def web_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = _on_off(context)
    if value is None:
        await update.message.reply_text("Usage: /web on or /web off" + status_text(update))
        return
    _session(update).use_web = value
    await update.message.reply_text(f"Web search {'enabled' if value else 'disabled'}" + status_text(update))


@restricted
async def rag_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = _on_off(context)
    if value is None:
        await update.message.reply_text("Usage: /rag on or /rag off" + status_text(update))
        return
    session = _session(update)
    if value and not session.recent_pdfs and not (session._pdf_store and session._pdf_store.text_chunks):
        await update.message.reply_text("No PDF loaded yet. Send a PDF first.")
        return
    session.use_pdf = value
    await update.message.reply_text(f"PDF RAG {'enabled' if value else 'disabled'}" + status_text(update))


@restricted
async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(list_reminders(str(update.effective_chat.id)))


@restricted
async def stealth_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = _on_off(context)
    if value is None:
        await update.message.reply_text(
            "Usage: /stealth_mode on or /stealth_mode off\n\n"
            "Stealth Mode normalises writing style before a query is sent to the cloud model,\n"
            "making it harder to link your cloud queries to you (Experiment 5)."
        )
        return
    UserPreferences.toggle_stealth_mode(str(update.effective_user.id), value)
    await update.message.reply_text(
        f"Stealth Mode {'ENABLED' if value else 'DISABLED'}\n"
        "Applies to API-mode queries. Partial defence: see research/README.md, Experiment 5."
    )


@restricted
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    # basename() stops names like "../../x.pdf" escaping the PDF folder.
    filename = os.path.basename(document.file_name or "")
    if not filename.lower().endswith(".pdf"):
        await update.message.reply_text("Please upload a PDF file.")
        return

    session = _session(update)
    file_path = session.pdf_dir / filename
    tg_file = await document.get_file()
    await tg_file.download_to_drive(str(file_path))
    await update.message.reply_text("PDF received. Indexing...")

    try:
        # First access loads the embedding model, so keep it off the event loop too.
        count = await asyncio.to_thread(lambda: session.pdf_store.load_pdf(filename))
    except ValueError as e:
        await update.message.reply_text(f"Warning: {e}")
        return
    except Exception as e:
        logger.error("PDF processing failed", exc_info=True)
        await update.message.reply_text(f"PDF processing error:\n{e}")
        return

    session.use_pdf = True
    session.recent_pdfs = (session.recent_pdfs + [str(file_path)])[-2:]
    await update.message.reply_text(
        f"PDF indexed: {filename}\n{count} chunks added. RAG is now ON.\n"
        + ("2 PDFs loaded. Say 'compare the two PDFs' to compare." if len(session.recent_pdfs) == 2 else "")
    )


@restricted
async def clear_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = _session(update)
    if session._pdf_store is not None:
        session._pdf_store.clear()
    session.recent_pdfs = []
    session.use_pdf = False
    await update.message.reply_text("PDF memory cleared. RAG turned OFF." + status_text(update))


@restricted
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not VOICE_AVAILABLE:
        await update.message.reply_text(
            "Voice is not available.\nInstall: pip install -r requirements-voice.txt\n"
            "and ffmpeg (https://ffmpeg.org/download.html)."
        )
        return
    await update.message.reply_text("Transcribing voice message...")
    voice = update.message.voice
    tg_file = await voice.get_file()
    fd, file_path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)
    try:
        await tg_file.download_to_drive(file_path)
        transcript = await asyncio.to_thread(transcribe_audio, file_path)
    finally:
        Path(file_path).unlink(missing_ok=True)

    if transcript.startswith("Error"):
        await update.message.reply_text(transcript)
        return
    await update.message.reply_text(f"You said: {transcript}")
    await _answer(update, context, transcript)


@restricted
async def share_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _answer(update, context, "/share_location")


@restricted
async def handle_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _answer(update, context, update.message.text)


@restricted
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    await _answer(update, context, f"/location:{loc.latitude}:{loc.longitude}:Current Location")


# ── daily briefing ────────────────────────────────────────────────────────────

def _build_briefing(chat_id: str) -> str:
    from tools.calendar_tool import list_events
    from tools.email_tool import format_inbox, read_inbox
    from tools.google_tasks_tool import list_tasks
    from tools.weather_tool import get_weather

    sections = [f"Good morning! Daily briefing for {datetime.now().strftime('%B %d, %Y')}\n"]
    for title, fn in [
        ("Weather", lambda: get_weather(settings.DEFAULT_CITY)),
        ("Today's calendar", lambda: list_events(days_ahead=1)),
        ("Unread emails", lambda: format_inbox(read_inbox(max_results=3, unread_only=True))),
        ("Pending tasks", list_tasks),
        ("Reminders", lambda: list_reminders(chat_id)),
    ]:
        try:
            sections.append(f"{title}:\n{fn()}\n")
        except Exception as e:  # one failing service shouldn't kill the briefing
            sections.append(f"{title}: unavailable ({e})\n")
    return "\n".join(sections)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")
    if not settings.TELEGRAM_ALLOWED_USER_IDS and not settings.TELEGRAM_ALLOW_ALL:
        raise SystemExit(
            "No allowed users configured. Set TELEGRAM_ALLOWED_USER_IDS (comma-separated Telegram "
            "user ids) or TELEGRAM_CHAT_ID in .env. Message @userinfobot to find your id."
        )

    async def post_init(application):
        start_scheduler()
        restore_reminders(application.bot)
        if settings.TELEGRAM_CHAT_ID:
            chat_id = settings.TELEGRAM_CHAT_ID

            async def briefing():
                return await asyncio.to_thread(_build_briefing, chat_id)

            setup_daily_briefing(application.bot, chat_id, briefing)
        else:
            logger.warning("TELEGRAM_CHAT_ID not set - daily briefing disabled")

    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("api", set_api))
    app.add_handler(CommandHandler("local", set_local))
    app.add_handler(CommandHandler("web", web_cmd))
    app.add_handler(CommandHandler("rag", rag_cmd))
    app.add_handler(CommandHandler("clearpdf", clear_pdf))
    app.add_handler(CommandHandler("reminders", reminders_cmd))
    app.add_handler(CommandHandler("stealth_mode", stealth_mode_cmd))
    app.add_handler(CommandHandler("share_location", share_location))

    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_text))

    logger.info(f"Telegram bot starting ({len(settings.TELEGRAM_ALLOWED_USER_IDS)} allowed user(s))")
    app.run_polling()


if __name__ == "__main__":
    main()
