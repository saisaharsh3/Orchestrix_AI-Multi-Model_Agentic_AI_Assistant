"""Google Calendar: list, delete, quick-add, and add-with-confirmation."""

import re
from datetime import timedelta

from core.handlers.base import Reply, Request
from tools.calendar_intent import detect_calendar_intent, extract_event_fields
from tools.calendar_tool import add_event, delete_event, list_events, parse_event_datetime, quick_add_event

CONFIRM_WORDS = {"yes", "confirm", "add it", "ok"}
CANCEL_WORDS = {"no", "cancel"}


def handle_pending(req: Request) -> Reply | None:
    state = req.session.calendar
    if not state["pending"]:
        return None

    if req.lower in CONFIRM_WORDS:
        start = state["start"]
        end = state["end"] or (start + timedelta(hours=1) if start else None)
        result = add_event(title=state["title"], start=start, end=end, location=state["location"])
        req.session.reset_calendar()
        return Reply(result)

    if req.lower in CANCEL_WORDS:
        req.session.reset_calendar()
        return Reply("Event cancelled.")

    return Reply(f"Pending calendar event:\n\n{_preview(state)}\n\nReply YES to add or NO to cancel.")


def handle(req: Request) -> Reply | None:
    intent = detect_calendar_intent(req.text)
    if intent is None:
        return None

    if intent == "list":
        return Reply(list_events(days_ahead=7))

    if intent == "delete":
        m = re.search(r"(?:delete|remove|cancel)\s+(?:event\s+)?(.+?)(?:\s+from\s+calendar)?$", req.lower)
        return Reply(delete_event(m.group(1).strip() if m else req.text))

    if intent == "quick_add":
        return Reply(quick_add_event(req.text))

    if intent == "add":
        fields = extract_event_fields(req.text)
        start = parse_event_datetime(req.text)
        if start is None:
            return Reply("When is it? Try e.g. 'add meeting with Ravi tomorrow at 3pm'.")
        req.session.calendar.update(
            pending=True,
            title=fields["title"],
            start=start,
            end=start + timedelta(hours=fields.get("duration_hr", 1)),
            location=fields.get("location", ""),
        )
        return Reply(f"Add to Google Calendar?\n\n{_preview(req.session.calendar)}\n\nReply YES to confirm or NO to cancel.")

    return None


def _preview(state: dict) -> str:
    when = state["start"].strftime("%b %d, %Y %I:%M %p") if state["start"] else "TBD"
    text = f"Title   : {state['title']}\nTime    : {when}"
    if state["location"]:
        text += f"\nLocation: {state['location']}"
    return text
