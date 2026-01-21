from datetime import datetime
from core.model_manager import generate_llm
from tools.web_search import web_search
from tools.wiki_search import wiki_search
from tools.news_search import news_search
from tools.email_intent import detect_email_intent, extract_email_fields
from tools.email_tool import send_email
from tools.web_automation.intent import detect_web_intent
from tools.web_automation.planner import WEB_STATE, reset_web_state
from tools.web_automation.youtube import open_youtube, search_youtube
from tools.web_automation.bookmyshow import open_bookmyshow, start_booking

def is_fact_question(text: str) -> bool:
    t = text.lower()
    return any(
        k in t
        for k in (
            "who is",
            "current",
            "cm of",
            "chief minister",
            "prime minister",
            "president",
        )
    )

EMAIL_STATE = {
    "pending": False,
    "to": "",
    "subject": "",
    "body": "",
}

def generate_response(
    user_input: str,
    model_type: str = "api",
    pdf_store=None,
    use_web: bool = True,
) -> str:

    today = datetime.now().strftime("%B %d, %Y")
    user_lower = user_input.lower().strip()
    context_blocks = []

    if user_lower in {"stop automation", "abort booking", "stop booking"}:
        reset_web_state()
        return " Automation stopped."

    if EMAIL_STATE["pending"]:
        if user_lower in {"yes", "send", "confirm"}:
            send_email(
                EMAIL_STATE["to"],
                EMAIL_STATE["subject"],
                EMAIL_STATE["body"],
            )
            EMAIL_STATE["pending"] = False
            return " Email sent successfully."

        if user_lower in {"no", "cancel"}:
            EMAIL_STATE["pending"] = False
            return " Email cancelled."

        return (
            " Pending email confirmation:\n\n"
            f"To: {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            "Reply YES to send or NO to cancel."
        )

    if detect_email_intent(user_input):
        extracted = extract_email_fields(user_input)
        missing = extracted.get("missing", [])

        if missing:
            return " Missing details: " + ", ".join(missing)

        EMAIL_STATE.update(
            pending=True,
            to=extracted["to"],
            subject=extracted.get("subject", ""),
            body=extracted["body"],
        )

        return (
            " Please confirm the email:\n\n"
            f"To: {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            "Reply YES to send or NO to cancel."
        )

    web_intent = detect_web_intent(user_input)

    if web_intent:
        intent = web_intent["type"]

        if intent == "youtube_open":
            return open_youtube()

        if intent == "youtube_search":
            return search_youtube(web_intent["query"])

        if intent == "bookmyshow_open":
            return open_bookmyshow()

        if intent == "book_movie":
            WEB_STATE.clear()
            WEB_STATE.update(
                {
                    "active": True,
                    "type": "movie",
                    "step": "city",
                    "data": {"movie": web_intent["movie"]},
                }
            )
            return f" Booking started for **{web_intent['movie']}**.\nWhich city?"

    if WEB_STATE.get("active") and WEB_STATE.get("type") == "movie":

        if WEB_STATE["step"] == "city":
            WEB_STATE["data"]["city"] = user_input
            WEB_STATE["step"] = "date"
            return " Which date? (today / tomorrow / DD-MM)"

        if WEB_STATE["step"] == "date":
            WEB_STATE["data"]["date"] = user_input
            WEB_STATE["step"] = "time"
            return " Preferred time? (e.g. 6:40 pm)"

        if WEB_STATE["step"] == "time":
            WEB_STATE["data"]["time"] = user_input
            WEB_STATE["step"] = "confirm"
            d = WEB_STATE["data"]

            return (
                " Please confirm booking:\n\n"
                f"Movie: {d['movie']}\n"
                f"City: {d['city']}\n"
                f"Date: {d['date']}\n"
                f"Time: {d['time']}\n"
                "Seats: Best available\n\n"
                "Reply YES to proceed or NO to cancel."
            )

        if WEB_STATE["step"] == "confirm":
            if user_lower in {"yes", "confirm"}:
                d = WEB_STATE["data"]
                reset_web_state()
                return start_booking(
                    d["movie"], d["city"], d["date"], d["time"]
                )

            if user_lower in {"no", "cancel"}:
                reset_web_state()
                return " Booking cancelled."

            return (
                "⏸ Booking paused.\n"
                "Reply YES to continue or NO to cancel.\n"
                "You may ask other questions meanwhile."
            )

    if pdf_store is not None:

        try:
            pdf_hits = pdf_store.smart_search(user_input)
        except Exception:
            pdf_hits = []

        if pdf_hits:
            prompt = f"""
You are a document-aware assistant.

INSTRUCTIONS:
- Answer using ONLY the PDF content below
- You may summarize or explain
- Do NOT add outside knowledge
- If info is incomplete, say so

PDF CONTENT:
{chr(10).join(pdf_hits)}

QUESTION:
{user_input}
""".strip()

            return generate_llm(prompt, model_type)

        
        if not use_web:
            return " The information is not available in the loaded PDF."

    if is_fact_question(user_input):
        fact = wiki_search(user_input)
        if fact:
            return fact

    if use_web:
        news_hits = news_search(user_input)
        if news_hits:
            context_blocks.append("NEWS:\n" + "\n".join(news_hits))

    if use_web:
        web_hits = web_search(user_input)
        if web_hits:
            context_blocks.append("WEB:\n" + "\n".join(web_hits))

    prompt = f"""
You are a careful AI assistant.

DATE: {today}

RULES:
- Do not invent facts
- Say clearly when information is missing

{chr(10).join(context_blocks)}

QUESTION:
{user_input}
""".strip()

    return generate_llm(prompt, model_type)
