import os
import re
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from core.orchestrator import generate_response
from core.model_manager import generate_llm
from rag.vector_store import PDFVectorStore

from tools.weather_tool import get_weather, get_forecast
from tools.finance_tool import convert_currency, get_stock_price, get_crypto_price
from tools.url_tool import summarize_url, track_price, show_tracked_prices
from tools.google_tasks_tool import add_task, list_tasks, complete_task, delete_task
from tools.google_drive_tool import search_drive, list_recent_files, list_shared_files
from tools.feature_intent import detect_feature_intent
from tools.scheduler import (
    schedule_reminder, list_reminders, cancel_reminder,
    setup_daily_briefing, restore_reminders, start_scheduler,
)

try:
    from tools.voice_tool import transcribe_audio
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TIMEZONE  = "Asia/Kolkata"

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in .env file")

model   = "local"
use_web = True
use_pdf = False

pdf_store    = PDFVectorStore()
pending_pdfs = []

PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs("reports", exist_ok=True)


def status_text():
    chunks = len(pdf_store.text_chunks)
    files  = ", ".join(pdf_store.loaded_files) if pdf_store.loaded_files else "none"
    return (
        f"\n\nSystem Status\n"
        f"Model  : {model.upper()}\n"
        f"Web    : {'ON' if use_web else 'OFF'}\n"
        f"RAG    : {'ON' if use_pdf else 'OFF'}\n"
        f"Chunks : {chunks}\n"
        f"PDFs   : {files}"
    )


def _parse_reminder_time(time_str: str, day: str = "today") -> datetime | None:
    try:
        from datetime import timedelta
        now = datetime.now(ZoneInfo(TIMEZONE))
        m   = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", time_str.lower())
        if not m:
            return None
        hour   = int(m.group(1))
        minute = int(m.group(2) or 0)
        period = m.group(3)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        if day == "tomorrow":
            base = now + timedelta(days=1)
        else:
            base = now
        dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Only auto-advance for today if time already passed
        if day == "today" and dt <= now:
            dt += timedelta(days=1)
        return dt
    except Exception:
        return None


async def _daily_briefing():
    from tools.weather_tool import get_weather
    from tools.email_tool import read_inbox, format_inbox
    from tools.calendar_tool import list_events
    parts = [f"Good morning! Daily briefing for {datetime.now().strftime('%B %d, %Y')}\n"]
    parts.append(f"Weather:\n{get_weather('Hyderabad')}\n")
    parts.append(f"Today's calendar:\n{list_events(days_ahead=1)}\n")
    emails = read_inbox(max_results=3, unread_only=True)
    parts.append(f"Unread emails:\n{format_inbox(emails)}")
    parts.append(f"Pending tasks:\n{list_tasks()}")
    return "\n".join(parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Orchestrix AI Connected!\n\n"
        "Commands:\n"
        "/api /local - switch model\n"
        "/web on|off - toggle web search\n"
        "/rag on|off - toggle PDF mode\n"
        "/clearpdf   - clear PDFs\n"
        "/status     - current settings\n"
        "/reminders  - list reminders\n\n"
        "What you can say:\n"
        "- weather in Mumbai\n"
        "- convert 500 USD to INR\n"
        "- TCS stock price\n"
        "- add task buy milk\n"
        "- show my tasks\n"
        "- find my resume on drive\n"
        "- remind me to call mom at 6pm\n"
        "- summarize https://...\n"
        "- track price https://...\n"
        "- compare the two PDFs\n"
        "- open youtube / set alarm for 7am\n\n"
        "Send a voice message to transcribe it.\n"
        "Send a PDF to index it for Q&A."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Current status:" + status_text())


async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global model
    model = "api"
    await update.message.reply_text("Switched to API model" + status_text())


async def set_local(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global model
    model = "local"
    await update.message.reply_text("Switched to LOCAL model" + status_text())


async def web_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_web
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        await update.message.reply_text("Usage: /web on or /web off" + status_text())
        return
    use_web = context.args[0].lower() == "on"
    await update.message.reply_text(
        f"Web search {'enabled' if use_web else 'disabled'}" + status_text()
    )


async def rag_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_pdf
    if not context.args or context.args[0].lower() not in {"on", "off"}:
        await update.message.reply_text("Usage: /rag on or /rag off" + status_text())
        return
    if context.args[0].lower() == "on" and not pdf_store.text_chunks:
        await update.message.reply_text("No PDF loaded yet. Send a PDF first.")
        return
    use_pdf = context.args[0].lower() == "on"
    await update.message.reply_text(
        f"PDF RAG {'enabled' if use_pdf else 'disabled'}" + status_text()
    )


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(list_reminders())


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_pdf
    document = update.message.document
    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("Please upload a PDF file.")
        return
    file_path = os.path.join(PDF_DIR, document.file_name)
    tg_file   = await document.get_file()
    await tg_file.download_to_drive(file_path)
    await update.message.reply_text("PDF received. Indexing...")
    try:
        count   = pdf_store.load_pdf(document.file_name)
        use_pdf = True
        pending_pdfs.append(file_path)
        if len(pending_pdfs) > 2:
            pending_pdfs.pop(0)
        await update.message.reply_text(
            f"PDF indexed: {document.file_name}\n"
            f"{count} chunks added. RAG is now ON.\n"
            + ("2 PDFs loaded. Say 'compare the two PDFs' to compare." if len(pending_pdfs) == 2 else "")
        )
    except ValueError as e:
        await update.message.reply_text(f"Warning: {e}")
    except Exception as e:
        await update.message.reply_text(f"PDF processing error:\n{e}")


async def clear_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global use_pdf
    pdf_store.clear()
    pending_pdfs.clear()
    use_pdf = False
    await update.message.reply_text("PDF memory cleared. RAG turned OFF." + status_text())


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not VOICE_AVAILABLE:
        await update.message.reply_text(
            "Voice not available.\n"
            "Run: pip install openai-whisper\n"
            "And install ffmpeg from https://ffmpeg.org/download.html"
        )
        return
    await update.message.reply_text("Transcribing voice message...")
    try:
        voice     = update.message.voice
        tg_file   = await voice.get_file()
        file_path = f"temp_voice_{voice.file_unique_id}.ogg"
        await tg_file.download_to_drive(file_path)
        transcript = transcribe_audio(file_path)
        try:
            os.unlink(file_path)
        except Exception:
            pass
        if transcript.startswith("Error"):
            await update.message.reply_text(transcript)
            return
        await update.message.reply_text(f"You said: {transcript}")
        response = generate_response(
            user_input=transcript,
            model_type=model,
            pdf_store=pdf_store,
            use_web=use_web,
            use_pdf=use_pdf,
        )
        MAX_LEN = 4096
        for i in range(0, len(response), MAX_LEN):
            await update.message.reply_text(response[i:i + MAX_LEN])
    except Exception as e:
        await update.message.reply_text(f"Voice error: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id    = str(update.effective_chat.id)
    lower      = user_input.lower()

    await update.message.reply_text("Thinking...")

    feat = detect_feature_intent(user_input)
    if feat:
        t = feat["type"]
        result = None

        if t == "weather_current":
            result = get_weather(feat["city"])
        elif t == "weather_forecast":
            result = get_forecast(feat["city"], days=3)
        elif t == "currency_convert":
            result = convert_currency(feat["amount"], feat["from_curr"], feat["to_curr"])
        elif t == "stock_price":
            result = get_stock_price(feat["ticker"])
        elif t == "crypto_price":
            result = get_crypto_price(feat["symbol"])
        elif t == "summarize_url":
            await update.message.reply_text("Fetching and summarizing URL...")
            result = summarize_url(feat["url"], generate_llm, model)
        elif t == "track_price":
            result = track_price(feat["url"])
        elif t == "show_tracked_prices":
            result = show_tracked_prices()
        elif t == "task_add":
            result = add_task(feat["title"])
        elif t == "task_list":
            result = list_tasks()
        elif t == "task_complete":
            result = complete_task(feat["keyword"])
        elif t == "task_delete":
            result = delete_task(feat["keyword"])
        elif t == "drive_search":
            result = search_drive(feat["query"])
        elif t == "drive_recent":
            result = list_recent_files()
        elif t == "drive_shared":
            result = list_shared_files()
        elif t == "reminder_set":
            dt = _parse_reminder_time(feat["time"], feat.get("day", "today"))
            if dt:
                bot    = context.application.bot
                result = schedule_reminder(bot, chat_id, feat["message"], dt)
            else:
                result = "Could not parse reminder time. Try: remind me to call mom at 6pm"
        elif t == "reminder_list":
            result = list_reminders()
        elif t == "reminder_cancel":
            result = cancel_reminder(feat["keyword"])
        elif t == "pdf_compare":
            if len(pending_pdfs) < 2:
                result = "Please upload two PDFs first, then say 'compare the two PDFs'."
            else:
                from tools.pdf_compare_tool import compare_pdfs
                await update.message.reply_text("Comparing PDFs...")
                result = compare_pdfs(pending_pdfs[0], pending_pdfs[1], generate_llm, model)
        elif t == "pdf_report":
            if not pdf_store.loaded_files:
                result = "No PDF loaded. Send a PDF first."
            else:
                from tools.pdf_compare_tool import summarize_pdf_to_report
                await update.message.reply_text("Generating PDF report...")
                pdf_name = list(pdf_store.loaded_files)[0]
                pdf_path = os.path.join(PDF_DIR, pdf_name)
                output   = summarize_pdf_to_report(pdf_path, generate_llm, model)
                if output.startswith("Error"):
                    result = output
                else:
                    await update.message.reply_document(
                        document=open(output, "rb"),
                        filename=os.path.basename(output),
                        caption=f"Summary report for {pdf_name}",
                    )
                    result = None

        if result:
            MAX_LEN = 4096
            for i in range(0, len(result), MAX_LEN):
                await update.message.reply_text(result[i:i + MAX_LEN])
        return

    if not use_pdf and any(w in lower for w in ("pdf", "document", "file")):
        if pdf_store.text_chunks:
            await update.message.reply_text(
                "Tip: A PDF is loaded but RAG is OFF. Send /rag on to query it."
            )

    try:
        response = generate_response(
            user_input=user_input,
            model_type=model,
            pdf_store=pdf_store,
            use_web=use_web,
            use_pdf=use_pdf,
        )
        MAX_LEN = 4096
        for i in range(0, len(response), MAX_LEN):
            await update.message.reply_text(response[i:i + MAX_LEN])
    except Exception as e:
        await update.message.reply_text(f"Error:\n{e}")


def main():
    async def post_init(application):
        start_scheduler()
        if CHAT_ID:
            restore_reminders(application.bot, CHAT_ID)
            setup_daily_briefing(application.bot, CHAT_ID, _daily_briefing)
        else:
            print(
                "Warning: TELEGRAM_CHAT_ID not set in .env"
            )

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("status",    status_cmd))
    app.add_handler(CommandHandler("api",       set_api))
    app.add_handler(CommandHandler("local",     set_local))
    app.add_handler(CommandHandler("web",       web_cmd))
    app.add_handler(CommandHandler("rag",       rag_cmd))
    app.add_handler(CommandHandler("clearpdf",  clear_pdf))
    app.add_handler(CommandHandler("reminders", reminders_cmd))

    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.VOICE,        handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()