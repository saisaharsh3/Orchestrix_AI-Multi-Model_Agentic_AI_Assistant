import re
from datetime import datetime

from core.model_manager import generate_llm
from core.prompt_builder import build_rag_prompt, build_general_prompt, build_web_prompt
from tools.web_search import web_search
from tools.wiki_search import wiki_search
from tools.news_search import news_search

from tools.email_intent import detect_email_intent, extract_email_fields, build_email_body
from tools.email_tool import (
    send_email, save_draft, read_inbox, format_inbox,
    reply_to_email, forward_email, search_emails,
)
from tools.calendar_intent import detect_calendar_intent, extract_event_fields
from tools.calendar_tool import (
    add_event, quick_add_event, list_events,
    delete_event, parse_event_datetime,
)

from tools.web_automation.intent import detect_web_intent
from tools.web_automation.planner import WEB_STATE, reset_web_state
from tools.web_automation.youtube import open_youtube, search_youtube, play_youtube
from tools.web_automation.bookmyshow import open_bookmyshow, start_booking
from tools.web_automation.phone_actions import (
    make_call, dial_number,
    open_whatsapp, whatsapp_message,
    open_spotify, spotify_search,
    play_pause_media, next_track, previous_track,
    open_maps, navigate_to, search_maps,
    set_alarm, set_timer,
    volume_up, volume_down, set_volume_percent, mute_phone,
    set_brightness_percent,
    open_camera, take_screenshot,
    open_app, connect_phone_wifi,
)


def is_fact_question(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in (
        "who is", "current", "cm of", "chief minister",
        "prime minister", "president",
    ))


EMAIL_STATE = {
    "pending":  False,
    "action":   "send",
    "to":       "",
    "subject":  "",
    "body":     "",
    "tone":     "professional",
    "msg_id":   "",
}

CALENDAR_STATE = {
    "pending":  False,
    "title":    "",
    "start":    None,
    "end":      None,
    "location": "",
}


def generate_response(
    user_input: str,
    model_type: str = "api",
    pdf_store=None,
    use_web: bool = True,
    use_pdf: bool = False,
) -> str:

    today = datetime.now().strftime("%B %d, %Y")
    user_input = user_input.strip()
    user_lower = user_input.lower()
    context_blocks = []

    # ── /help ──────────────────────────────────────────────────────────────
    if user_lower == "/help":
        return (
            " *Orchestrix AI – Help*\n\n"
            "/api – API model\n"
            "/local – Local model\n"
            "/web on | off\n"
            "/rag on | off\n"
            "/clearpdf\n\n"
            " *Phone Commands* (requires ADB):\n"
            "• open youtube / search youtube for <query>\n"
            "• open spotify / play <song> on spotify\n"
            "• call <number> / dial <number>\n"
            "• whatsapp <number> <message>\n"
            "• navigate to <place> / search maps <place>\n"
            "• set alarm for HH:MM / set timer for Xm Ys\n"
            "• volume up/down / set volume to X%\n"
            "• set brightness to X%\n"
            "• open camera / take screenshot\n"
            "• open <app-name>\n"
            "• connect phone <ip-address>\n\n"
            "Ask questions anytime."
        )

    # ── Stop automation ────────────────────────────────────────────────────
    if user_lower in {"stop automation", "abort booking", "stop booking"}:
        reset_web_state()
        return " Automation stopped."

    # ── Email confirmation flow ────────────────────────────────────────────
    if EMAIL_STATE["pending"]:
        if user_lower in {"yes", "send", "confirm"}:
            action = EMAIL_STATE["action"]
            if action == "draft":
                result = save_draft(EMAIL_STATE["to"], EMAIL_STATE["subject"], EMAIL_STATE["body"])
            elif action == "reply":
                result = reply_to_email(EMAIL_STATE["msg_id"], EMAIL_STATE["body"])
            elif action == "forward":
                result = forward_email(EMAIL_STATE["msg_id"], EMAIL_STATE["to"])
            else:
                result = send_email(EMAIL_STATE["to"], EMAIL_STATE["subject"], EMAIL_STATE["body"])
            EMAIL_STATE["pending"] = False
            return result

        if user_lower in {"no", "cancel"}:
            EMAIL_STATE["pending"] = False
            return " Email cancelled."

        return (
            " Pending confirmation:\n\n"
            f"Action : {EMAIL_STATE['action'].upper()}\n"
            f"To     : {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            "Reply YES to confirm or NO to cancel."
        )

    # ── Calendar confirmation flow ─────────────────────────────────────────
    if CALENDAR_STATE["pending"]:
        if user_lower in {"yes", "confirm", "add it", "ok"}:
            from datetime import timedelta
            start = CALENDAR_STATE["start"]
            end   = CALENDAR_STATE["end"] or (start + timedelta(hours=1) if start else None)
            result = add_event(
                title=CALENDAR_STATE["title"],
                start=start,
                end=end,
                location=CALENDAR_STATE["location"],
            )
            CALENDAR_STATE["pending"] = False
            return result

        if user_lower in {"no", "cancel"}:
            CALENDAR_STATE["pending"] = False
            return " Event cancelled."

        return (
            " Pending calendar event:\n\n"
            f"Title   : {CALENDAR_STATE['title']}\n"
            f"Time    : {CALENDAR_STATE['start'].strftime('%b %d, %Y %I:%M %p') if CALENDAR_STATE['start'] else 'TBD'}\n"
            + (f"Location: {CALENDAR_STATE['location']}\n" if CALENDAR_STATE['location'] else "")
            + "\nReply YES to add or NO to cancel."
        )

    # ── Read inbox (no confirmation needed) ───────────────────────────────
    email_intent = detect_email_intent(user_input)

    if email_intent == "read":
        emails = read_inbox(max_results=5, unread_only=True)
        return format_inbox(emails)

    if email_intent == "send" and re.search(r"search|find|look for", user_lower):
        # "search my email for X"
        m = re.search(r"(?:search|find|look for)\s+(?:email[s]?\s+(?:about|from|for)\s+)?(.+)", user_lower)
        query = m.group(1).strip() if m else user_input
        return search_emails(query)

    if email_intent in {"send", "draft", "reply", "forward"}:
        extracted = extract_email_fields(user_input)
        missing   = extracted.get("missing", [])
        if missing:
            return " Please provide: " + ", ".join(missing)

        body = extracted.get("body") or ""
        # Always use API model for email body expansion regardless of current model
        # Local model is not reliable enough for composing emails
        if len(body.split()) < 8 and extracted.get("subject"):
            prompt = build_email_body(extracted["subject"], body or extracted["subject"], extracted.get("tone", "professional"))
            body = generate_llm(prompt, "api")
        elif not body and extracted.get("subject"):
            body = extracted["subject"]

        EMAIL_STATE.update(
            pending=True,
            action=email_intent,
            to=extracted["to"] or "",
            subject=extracted.get("subject") or "",
            body=body,
            tone=extracted.get("tone", "professional"),
        )
        return (
            f" Confirm {email_intent.upper()}:\n\n"
            f"To     : {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            "Reply YES to send or NO to cancel."
        )

    # ── Calendar intent ────────────────────────────────────────────────────
    cal_intent = detect_calendar_intent(user_input)

    if cal_intent == "list":
        return list_events(days_ahead=7)

    if cal_intent == "delete":
        m = re.search(r"(?:delete|remove|cancel)\s+(?:event\s+)?(.+?)(?:\s+from\s+calendar)?$", user_lower)
        title = m.group(1).strip() if m else user_input
        return delete_event(title)

    if cal_intent == "quick_add":
        return quick_add_event(user_input)

    if cal_intent == "add":
        fields = extract_event_fields(user_input)
        start  = parse_event_datetime(user_input)
        from datetime import timedelta
        end = start + timedelta(hours=fields.get("duration_hr", 1)) if start else None

        CALENDAR_STATE.update(
            pending=True,
            title=fields["title"],
            start=start,
            end=end,
            location=fields.get("location", ""),
        )
        return (
            f" Add to Google Calendar?\n\n"
            f"*{CALENDAR_STATE['title']}*\n"
            f" {start.strftime('%b %d, %Y %I:%M %p') if start else 'Time unknown'}\n"
            + (f" {CALENDAR_STATE['location']}\n" if CALENDAR_STATE['location'] else "")
            + "\nReply YES to confirm or NO to cancel."
        )

    # ── Web / Phone automation intent ──────────────────────────────────────
    web_intent = detect_web_intent(user_input)
    if web_intent:
        t = web_intent["type"]

        # Phone Wi-Fi ADB
        if t == "connect_phone_wifi":
            return connect_phone_wifi(web_intent["ip"])

        # YouTube
        if t == "youtube_open":
            return open_youtube()
        if t == "youtube_search":
            return search_youtube(web_intent["query"])

        # Spotify
        if t == "spotify_open":
            return open_spotify()
        if t == "spotify_search":
            return spotify_search(web_intent["query"])

        # Media
        if t == "media_play_pause":
            return play_pause_media()
        if t == "media_next":
            return next_track()
        if t == "media_prev":
            return previous_track()

        # Calls
        if t == "make_call":
            return make_call(web_intent["number"])
        if t == "dial":
            return dial_number(web_intent["number"])

        # WhatsApp
        if t == "whatsapp_open":
            return open_whatsapp()
        if t == "whatsapp_message":
            return whatsapp_message(web_intent["number"], web_intent["message"])

        # Maps
        if t == "maps_open":
            return open_maps()
        if t == "navigate":
            return navigate_to(web_intent["destination"])
        if t == "maps_search":
            return search_maps(web_intent["query"])

        # Alarms & Timers
        if t == "set_alarm":
            return set_alarm(web_intent["hour"], web_intent["minute"])
        if t == "set_timer":
            return set_timer(web_intent["seconds"])

        # Volume
        if t == "mute":
            return mute_phone()
        if t == "set_volume":
            return set_volume_percent(web_intent["percent"])
        if t == "volume_up":
            return volume_up(web_intent.get("steps", 1))
        if t == "volume_down":
            return volume_down(web_intent.get("steps", 1))

        # Brightness
        if t == "set_brightness":
            return set_brightness_percent(web_intent["percent"])

        # Camera
        if t == "camera_open":
            return open_camera()
        if t == "screenshot":
            return take_screenshot()

        # Generic app
        if t == "open_app":
            return open_app(web_intent["app"])

        # BookMyShow
        if t == "bookmyshow_open":
            return open_bookmyshow()
        if t == "book_movie":
            WEB_STATE.clear()
            WEB_STATE.update({
                "active": True,
                "type": "movie",
                "step": "city",
                "data": {"movie": web_intent["movie"]},
            })
            return f" Booking started for *{web_intent['movie']}*.\nWhich city?"

    # ── Active booking flow ────────────────────────────────────────────────
    if WEB_STATE.get("active"):
        step = WEB_STATE["step"]
        data = WEB_STATE["data"]

        if step == "city":
            data["city"] = user_input
            WEB_STATE["step"] = "date"
            return " Which date?"

        if step == "date":
            data["date"] = user_input
            WEB_STATE["step"] = "time"
            return " Preferred time?"

        if step == "time":
            data["time"] = user_input
            WEB_STATE["step"] = "confirm"
            return (
                f" Confirm booking:\n"
                f"Movie : {data.get('movie')}\n"
                f"City  : {data.get('city')}\n"
                f"Date  : {data.get('date')}\n"
                f"Time  : {data.get('time')}\n\n"
                "Reply YES or NO."
            )

        if step == "confirm":
            if user_lower == "yes":
                reset_web_state()
                return start_booking(data["movie"], data["city"], data["date"], data["time"])
            reset_web_state()
            return " Booking cancelled."

    # ── PDF RAG ────────────────────────────────────────────────────────────
    # FIX: use_pdf AND pdf_store must both be truthy; prompt is now strongly grounded
    if use_pdf and pdf_store is not None:
        pdf_hits = pdf_store.smart_search(user_input, top_k=8)
        print(f"[DEBUG] PDF hits: {len(pdf_hits)}")

        if pdf_hits:
            prompt = build_rag_prompt(user_input, pdf_hits, model_type)
            return generate_llm(prompt, model_type)

        # Zero hits — fallback to first chunks for generic questions
        if pdf_store.text_chunks:
            fallback_chunks = pdf_store.text_chunks[:6]
            prompt = build_rag_prompt(user_input, fallback_chunks, model_type)
            return generate_llm(prompt, model_type)

        return (
            " No content found in the PDF. Try rephrasing your question."
        )

    # ── Fact / Wiki ────────────────────────────────────────────────────────
    if is_fact_question(user_input):
        fact = wiki_search(user_input)
        if fact:
            return fact

    # ── Web search ─────────────────────────────────────────────────────────
    if use_web:
        news = news_search(user_input)
        web  = web_search(user_input)
        if news:
            context_blocks.append("NEWS:\n" + "\n".join(news))
        if web:
            context_blocks.append("WEB:\n" + "\n".join(web))

    # ── Final LLM call ─────────────────────────────────────────────────────
    if use_web and context_blocks:
        news_items = [b.replace("NEWS:\n","") for b in context_blocks if b.startswith("NEWS:")]
        web_items  = [b.replace("WEB:\n","")  for b in context_blocks if b.startswith("WEB:")]
        prompt = build_web_prompt(user_input, news_items, web_items, model_type)
    else:
        prompt = build_general_prompt(user_input, context_blocks, model_type)

    return generate_llm(prompt, model_type)