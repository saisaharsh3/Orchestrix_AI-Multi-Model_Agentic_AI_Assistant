"""
intent.py — Web / Phone automation intent detection
─────────────────────────────────────────────────────
Returns a typed dict describing the detected intent, or None.
"""

import re


def detect_web_intent(text: str) -> dict | None:
    t = text.lower().strip()

    # ── Wi-Fi ADB connect ─────────────────────────────────────────────────
    m = re.search(r"connect\s+phone\s+([\d.]+)", t)
    if m:
        return {"type": "connect_phone_wifi", "ip": m.group(1)}

    # ── YouTube ───────────────────────────────────────────────────────────
    if re.search(r"open\s+youtube|launch\s+youtube|start\s+youtube", t):
        return {"type": "youtube_open"}

    m = re.search(r"(?:search|play|find)\s+(?:on\s+)?youtube\s+(?:for\s+)?(.+)", t)
    if m:
        return {"type": "youtube_search", "query": m.group(1).strip()}

    m = re.search(r"youtube\s+(?:search|play)\s+(.+)", t)
    if m:
        return {"type": "youtube_search", "query": m.group(1).strip()}

    # ── Spotify ───────────────────────────────────────────────────────────
    if re.search(r"open\s+spotify|launch\s+spotify", t):
        return {"type": "spotify_open"}

    m = re.search(r"(?:play|search)\s+(?:on\s+)?spotify\s+(?:for\s+)?(.+)", t)
    if m:
        return {"type": "spotify_search", "query": m.group(1).strip()}

    m = re.search(r"spotify\s+(?:play|search)\s+(.+)", t)
    if m:
        return {"type": "spotify_search", "query": m.group(1).strip()}

    # ── Media controls ────────────────────────────────────────────────────
    if re.search(r"\b(pause|resume|play\s+pause)\b", t) and re.search(r"\b(music|song|track|media)\b", t):
        return {"type": "media_play_pause"}

    if re.search(r"\bnext\s+(song|track|music)\b", t):
        return {"type": "media_next"}

    if re.search(r"\b(previous|prev|back)\s+(song|track|music)\b", t):
        return {"type": "media_prev"}

    # ── Phone calls ───────────────────────────────────────────────────────
    m = re.search(r"call\s+([\d\s\+\-\(\)]{7,})", t)
    if m:
        number = re.sub(r"[\s\-\(\)]", "", m.group(1))
        return {"type": "make_call", "number": number}

    m = re.search(r"dial\s+([\d\s\+\-\(\)]{7,})", t)
    if m:
        number = re.sub(r"[\s\-\(\)]", "", m.group(1))
        return {"type": "dial", "number": number}

    # ── WhatsApp ──────────────────────────────────────────────────────────
    if re.search(r"open\s+whatsapp|launch\s+whatsapp", t):
        return {"type": "whatsapp_open"}

    m = re.search(
        r"(?:whatsapp|message|text|send)\s+(?:message\s+)?(?:to\s+)?([\d\+]{7,})\s+(.+)", t
    )
    if m:
        return {
            "type": "whatsapp_message",
            "number": re.sub(r"[\s\-]", "", m.group(1)),
            "message": m.group(2).strip(),
        }

    # ── Google Maps ───────────────────────────────────────────────────────
    m = re.search(r"navigate\s+to\s+(.+)|directions?\s+to\s+(.+)", t)
    if m:
        dest = (m.group(1) or m.group(2)).strip()
        return {"type": "navigate", "destination": dest}

    m = re.search(r"(?:search|find|show)\s+(?:on\s+)?maps?\s+(.+)", t)
    if m:
        return {"type": "maps_search", "query": m.group(1).strip()}

    if re.search(r"open\s+maps?|launch\s+maps?", t):
        return {"type": "maps_open"}

    # ── Alarms & Timers ───────────────────────────────────────────────────
    m = re.search(r"set\s+(?:an?\s+)?alarm\s+(?:for\s+)?(\d{1,2})[:\.](\d{2})\s*(am|pm)?", t)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        period = m.group(3)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return {"type": "set_alarm", "hour": h, "minute": mn}

    m = re.search(
        r"set\s+(?:a\s+)?timer\s+(?:for\s+)?(?:(\d+)\s*(?:hours?|hrs?))?\s*(?:(\d+)\s*(?:minutes?|mins?))?\s*(?:(\d+)\s*(?:seconds?|secs?))?",
        t,
    )
    if m and any(m.groups()):
        hrs  = int(m.group(1) or 0)
        mins = int(m.group(2) or 0)
        secs = int(m.group(3) or 0)
        total = hrs * 3600 + mins * 60 + secs
        if total > 0:
            return {"type": "set_timer", "seconds": total}

    # ── Volume ────────────────────────────────────────────────────────────
    if re.search(r"mute\s+(?:the\s+)?phone|silence\s+phone", t):
        return {"type": "mute"}

    m = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d+)\s*%?", t)
    if m:
        return {"type": "set_volume", "percent": int(m.group(1))}

    if re.search(r"volume\s+up|increase\s+volume|louder", t):
        m2 = re.search(r"(\d+)\s*(?:steps?|times?|notches?)", t)
        return {"type": "volume_up", "steps": int(m2.group(1)) if m2 else 1}

    if re.search(r"volume\s+down|decrease\s+volume|lower\s+volume|quieter", t):
        m2 = re.search(r"(\d+)\s*(?:steps?|times?|notches?)", t)
        return {"type": "volume_down", "steps": int(m2.group(1)) if m2 else 1}

    # ── Brightness ────────────────────────────────────────────────────────
    m = re.search(r"(?:set\s+)?brightness\s+(?:to\s+)?(\d+)\s*%?", t)
    if m:
        return {"type": "set_brightness", "percent": int(m.group(1))}

    # ── Camera ────────────────────────────────────────────────────────────
    if re.search(r"open\s+camera|take\s+(?:a\s+)?photo|take\s+(?:a\s+)?picture", t):
        return {"type": "camera_open"}

    if re.search(r"take\s+(?:a\s+)?screenshot|capture\s+screen", t):
        return {"type": "screenshot"}

    # ── Open generic app ──────────────────────────────────────────────────
    m = re.search(
        r"open\s+(chrome|gmail|instagram|twitter|facebook|telegram|settings|calculator|clock|files|photos)",
        t,
    )
    if m:
        return {"type": "open_app", "app": m.group(1)}

    # ── BookMyShow ────────────────────────────────────────────────────────
    if re.search(r"open\s+bookmyshow|launch\s+bookmyshow", t):
        return {"type": "bookmyshow_open"}

    m = re.search(r"book\s+(?:a\s+)?(?:ticket\s+for\s+|movie\s+)?(.+?)(?:\s+movie|\s+ticket|$)", t)
    if m:
        return {"type": "book_movie", "movie": m.group(1).strip()}

    return None