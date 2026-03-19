"""
calendar_intent.py — Calendar intent detection
───────────────────────────────────────────────
Detects: add_event, list_events, delete_event, quick_add
"""

import re


ADD_TRIGGERS = [
    "add to calendar", "add event", "create event", "schedule",
    "set a meeting", "book a meeting", "remind me", "add meeting",
    "add to my calendar", "put on calendar", "create a reminder",
    "schedule a call", "add appointment", "block time",
]

LIST_TRIGGERS = [
    "what's on my calendar", "show my calendar", "my schedule",
    "upcoming events", "what do i have", "show events",
    "check my calendar", "list events", "what's scheduled",
    "any events", "my meetings", "today's schedule",
]

DELETE_TRIGGERS = [
    "delete event", "remove event", "cancel event",
    "delete from calendar", "remove from calendar",
    "cancel meeting", "delete meeting",
]


def detect_calendar_intent(text: str) -> str | None:
    """
    Returns: 'add' | 'list' | 'delete' | 'quick_add' | None
    """
    t = text.lower()

    if any(trigger in t for trigger in DELETE_TRIGGERS):
        return "delete"

    if any(trigger in t for trigger in LIST_TRIGGERS):
        return "list"

    if any(trigger in t for trigger in ADD_TRIGGERS):
        
        has_time = bool(re.search(r"\d{1,2}(?::\d{2})?\s*(?:am|pm)", t))
        has_date = bool(re.search(
            r"tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|\d{1,2}(?:st|nd|rd|th)?",
            t
        ))
        return "add" if (has_time or has_date) else "quick_add"

    
    if re.search(
        r"(meeting|call|appointment|interview|event|lunch|dinner|standup|sync)\s.*(tomorrow|today|at\s+\d|next\s+\w+day)",
        t
    ):
        return "quick_add"

    return None


def extract_event_fields(text: str) -> dict:
    """
    Extract title, duration, location, description from text.
    """
    result = {
        "title":       None,
        "duration_hr": 1,
        "location":    "",
        "description": "",
    }

    t = text.lower()

    
    dur_match = re.search(r"for\s+(\d+)\s*(hour|hr|minute|min)", t)
    if dur_match:
        val  = int(dur_match.group(1))
        unit = dur_match.group(2)
        result["duration_hr"] = val if "hour" in unit or "hr" in unit else val / 60

    
    loc_match = re.search(r"\bat\s+([A-Za-z][A-Za-z\s]{2,30})(?=\s|$)", text)
    if loc_match:
        loc = loc_match.group(1).strip()
        
        if not re.match(r"\d{1,2}(?::\d{2})?\s*(?:am|pm)", loc, re.IGNORECASE):
            result["location"] = loc

    
    title_match = re.search(
        r"(?:schedule|add|create|set|book|remind me (?:about|to)?)\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:\s+(?:tomorrow|today|on|at\s+\d|next|for\s+\d)|$)",
        text,
        re.IGNORECASE,
    )
    if title_match:
        result["title"] = title_match.group(1).strip().title()

    
    if not result["title"]:
        words = text.split()[:4]
        result["title"] = " ".join(words).title()

    return result