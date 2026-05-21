"""
calendar_tool.py — Google Calendar automation
───────────────────────────────────────────────
Supports: add event, list events, quick-add (natural language), delete event
Uses same Google OAuth credentials as Gmail.

Scopes needed in credentials/credentials.json:
  https://www.googleapis.com/auth/calendar
"""

import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_PATH = "credentials/credentials.json"
TOKEN_PATH       = "credentials/token.json"


DEFAULT_TIMEZONE = "Asia/Kolkata"




def _get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs("credentials", exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)




def add_event(
    title: str,
    start: datetime,
    end: datetime | None = None,
    description: str = "",
    location: str = "",
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    try:
        service = _get_calendar_service()

        if end is None:
            end = start + timedelta(hours=1)

        event = {
            "summary":     title,
            "description": description,
            "location":    location,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": timezone,
            },
        }

        created = service.events().insert(calendarId="primary", body=event).execute()
        link    = created.get("htmlLink", "")
        return (
            f" Event added!\n"
            f"*{title}*\n"
            f" {start.strftime('%b %d, %Y %I:%M %p')}"
            + (f" → {end.strftime('%I:%M %p')}" if end else "")
            + (f"\n {location}" if location else "")
            + (f"\n {link}" if link else "")
        )

    except HttpError as e:
        return f" Calendar error: {e}"
    except Exception as e:
        return f" Failed to add event: {e}"




def quick_add_event(text: str) -> str:
    """
    Uses Google Calendar's built-in NLP.
    Example: "Meeting with John tomorrow at 3pm"
    """
    try:
        service = _get_calendar_service()
        event   = service.events().quickAdd(calendarId="primary", text=text).execute()
        link    = event.get("htmlLink", "")
        title   = event.get("summary", text)
        start   = event.get("start", {}).get("dateTime", "")

        start_str = ""
        if start:
            dt = datetime.fromisoformat(start)
            start_str = dt.strftime("%b %d, %Y %I:%M %p")

        return (
            f" Event added!\n"
            f"*{title}*\n"
            + (f" {start_str}\n" if start_str else "")
            + (f" {link}" if link else "")
        )

    except HttpError as e:
        return f" Calendar error: {e}"
    except Exception as e:
        return f" Quick add failed: {e}"




def list_events(days_ahead: int = 7, max_results: int = 10) -> str:
    try:
        service  = _get_calendar_service()
        
        # Use local timezone for calculations
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        end_time = now + timedelta(days=days_ahead)

        # Convert to UTC for the API (RFC 3339 format with Z)
        # The API needs UTC times, so convert from local to UTC
        now_utc = now.astimezone(ZoneInfo("UTC"))
        end_utc = end_time.astimezone(ZoneInfo("UTC"))
        
        timeMin = now_utc.isoformat().replace("+00:00", "Z")
        timeMax = end_utc.isoformat().replace("+00:00", "Z")

        events_result = service.events().list(
            calendarId="primary",
            timeMin=timeMin,
            timeMax=timeMax,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        if not events:
            return f" No events in the next {days_ahead} day(s)."

        lines = [f" *Upcoming events ({days_ahead} days):*\n"]
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            try:
                dt       = datetime.fromisoformat(start.replace("Z", "+00:00"))
                tz       = ZoneInfo(DEFAULT_TIMEZONE)
                dt_local = dt.astimezone(tz)
                time_str = dt_local.strftime("%b %d, %I:%M %p")
            except Exception:
                time_str = start

            title    = e.get("summary", "(no title)")
            location = e.get("location", "")
            lines.append(
                f"• *{title}*\n"
                f"   {time_str}"
                + (f"   {location}" if location else "")
            )

        return "\n".join(lines)

    except HttpError as e:
        return f" Calendar error: {e}"
    except Exception as e:
        return f" Could not fetch events: {e}"




def delete_event(title: str) -> str:
    try:
        service = _get_calendar_service()
        
        # Use local timezone
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        
        # Convert to UTC for the API
        now_utc = now.astimezone(ZoneInfo("UTC"))
        timeMin = now_utc.isoformat().replace("+00:00", "Z")

        results = service.events().list(
            calendarId="primary",
            timeMin=timeMin,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
            q=title,
        ).execute()

        events = results.get("items", [])
        if not events:
            return f" No upcoming event found matching *{title}*."

        event    = events[0]
        event_id = event["id"]
        name     = event.get("summary", title)

        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f" Event deleted: *{name}*"

    except HttpError as e:
        return f" Calendar error: {e}"
    except Exception as e:
        return f" Delete failed: {e}"




def parse_event_datetime(text: str) -> datetime | None:
    """
    Parses common date/time expressions from user text.
    Returns a datetime object or None if unparseable.
    """
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    t   = text.lower()

    # "tomorrow at 3pm", "today at 5:30pm"
    time_match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t
    )
    hour   = None
    minute = 0

    if time_match:
        hour   = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        period = time_match.group(3)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

    base = now
    if "tomorrow" in t:
        base = now + timedelta(days=1)
    elif "day after tomorrow" in t:
        base = now + timedelta(days=2)
    elif "next week" in t:
        base = now + timedelta(weeks=1)
    elif "monday" in t:
        days_ahead = (0 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "tuesday" in t:
        days_ahead = (1 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "wednesday" in t:
        days_ahead = (2 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "thursday" in t:
        days_ahead = (3 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "friday" in t:
        days_ahead = (4 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "saturday" in t:
        days_ahead = (5 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)
    elif "sunday" in t:
        days_ahead = (6 - now.weekday()) % 7 or 7
        base = now + timedelta(days=days_ahead)

    # Specific date like "March 20" or "20th March"
    date_match = re.search(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})", t
    ) or re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", t
    )
    if date_match:
        try:
            date_str = date_match.group(0)
            base = datetime.strptime(date_str, "%B %d").replace(
                year=now.year, tzinfo=ZoneInfo(DEFAULT_TIMEZONE)
            )
        except Exception:
            pass

    if hour is not None:
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    
    return base.replace(hour=9, minute=0, second=0, microsecond=0)