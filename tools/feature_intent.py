"""
feature_intent.py - Intent detection for all new features
"""

import re


def detect_feature_intent(text: str) -> dict | None:
    t = text.lower().strip()

    # -- Weather --------------------------------------------------------------
    m = re.search(r"weather\s+(?:in\s+)?(.+?)(?:\s+tomorrow|\s+today|$)", t)
    if m:
        city    = m.group(1).strip()
        is_fore = "tomorrow" in t or "forecast" in t or "week" in t
        return {"type": "weather_forecast" if is_fore else "weather_current", "city": city}

    if re.search(r"weather|temperature|forecast|will it rain", t):
        return {"type": "weather_current", "city": "Hyderabad"}

    # -- Finance --------------------------------------------------------------
    m = re.search(r"convert\s+([\d,.]+)\s+([a-z]{3})\s+to\s+([a-z]{3})", t)
    if m:
        return {
            "type":      "currency_convert",
            "amount":    float(m.group(1).replace(",", "")),
            "from_curr": m.group(2).upper(),
            "to_curr":   m.group(3).upper(),
        }

    m = re.search(r"([\d,.]+)\s+([a-z]{3})\s+(?:to|in)\s+([a-z]{3})", t)
    if m:
        return {
            "type":      "currency_convert",
            "amount":    float(m.group(1).replace(",", "")),
            "from_curr": m.group(2).upper(),
            "to_curr":   m.group(3).upper(),
        }

    m = re.search(r"(?:price of|share price of)\s+([a-z0-9]+)", t)
    if m:
        return {"type": "stock_price", "ticker": m.group(1).upper()}

    m = re.search(r"([a-z]{2,10})\s+stock\s*(?:price)?", t)
    if m:
        ticker = m.group(1).upper()
        # Skip common words that are not tickers
        skip = {"THE", "A", "AN", "MY", "GET", "SHOW", "CHECK", "WHAT", "IS"}
        if ticker not in skip:
            return {"type": "stock_price", "ticker": ticker}

    m = re.search(r"stock\s+(?:price\s+(?:of\s+)?)?([a-z0-9]{2,10})", t)
    if m:
        return {"type": "stock_price", "ticker": m.group(1).upper()}

    m = re.search(r"(?:crypto|bitcoin|ethereum|btc|eth|sol)\s*(?:price)?", t)
    if m:
        symbol = "BTC"
        if "eth" in t:    symbol = "ETH"
        elif "sol" in t:  symbol = "SOL"
        elif re.search(r"([a-z]{3,5})\s+crypto", t):
            symbol = re.search(r"([a-z]{3,5})\s+crypto", t).group(1).upper()
        return {"type": "crypto_price", "symbol": symbol}

    # -- URL ------------------------------------------------------------------
    url_match = re.search(r"https?://[^\s]+", text)
    if url_match:
        url = url_match.group()
        if re.search(r"summar|explain|what is|tell me about|read", t):
            return {"type": "summarize_url", "url": url}
        if re.search(r"track\s+price|price\s+track|monitor\s+price", t):
            return {"type": "track_price", "url": url}

    if re.search(r"track(?:ed)?\s+prices?|show\s+tracked", t):
        return {"type": "show_tracked_prices"}

    # -- Tasks ----------------------------------------------------------------
    m = re.search(r"add\s+(?:task\s+|to(?:do|do list)?\s+)?(?:to\s+(?:my\s+)?(?:tasks?|todo)\s+)?(.+)", t)
    if m and re.search(r"add\s+(?:a\s+)?(?:task|todo|to my tasks|to my todo)", t):
        return {"type": "task_add", "title": m.group(1).strip()}

    if re.search(r"(?:show|list|my)\s+(?:tasks?|todos?)|what.*tasks?", t):
        return {"type": "task_list"}

    m = re.search(r"(?:complete|done|finish|mark)\s+(?:task\s+)?(.+)", t)
    if m:
        return {"type": "task_complete", "keyword": m.group(1).strip()}

    m = re.search(r"(?:delete|remove)\s+task\s+(.+)", t)
    if m:
        return {"type": "task_delete", "keyword": m.group(1).strip()}

    # -- Google Drive ---------------------------------------------------------
    m = re.search(r"(?:find|search|look for)\s+(?:file\s+|my\s+)?(.+?)\s+(?:in|on)\s+(?:google\s+)?drive", t)
    if m:
        return {"type": "drive_search", "query": m.group(1).strip()}

    m = re.search(r"(?:find|search)\s+(.+?)\s+(?:file|document|sheet|slide)", t)
    if m:
        return {"type": "drive_search", "query": m.group(1).strip()}

    if re.search(r"(?:recent|latest)\s+(?:files?|documents?)|(?:my\s+)?drive\s+files?", t):
        return {"type": "drive_recent"}

    if re.search(r"shared\s+(?:with\s+me\s+)?files?|files?\s+shared", t):
        return {"type": "drive_shared"}

    # -- Reminders ------------------------------------------------------------
    # Reminder with tomorrow/today + time
    m = re.search(
        r"remind\s+(?:me\s+)?(?:to\s+|about\s+)?(.+?)\s+(?:tomorrow|today)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        t,
    )
    if m:
        day = "tomorrow" if "tomorrow" in t else "today"
        return {
            "type":    "reminder_set",
            "message": m.group(1).strip(),
            "time":    m.group(2).strip(),
            "day":     day,
        }

    # Reminder with just time (no today/tomorrow — defaults to today, auto-advances if past)
    m = re.search(
        r"remind\s+(?:me\s+)?(?:to\s+|about\s+)?(.+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        t,
    )
    if m:
        msg = m.group(1).strip()
        # Exclude if message looks like a place ("at home", "at office")
        time_part = m.group(2).strip()
        return {
            "type":    "reminder_set",
            "message": msg,
            "time":    time_part,
            "day":     "today",
        }

    if re.search(r"(?:show|list|my)\s+reminders?", t):
        return {"type": "reminder_list"}

    m = re.search(r"cancel\s+reminder\s+(?:for\s+)?(.+)", t)
    if m:
        return {"type": "reminder_cancel", "keyword": m.group(1).strip()}

    # -- PDF compare / report -------------------------------------------------
    if re.search(r"compare\s+(?:the\s+)?(?:two\s+)?pdfs?", t):
        return {"type": "pdf_compare"}

    if re.search(r"(?:generate|create|make)\s+(?:a\s+)?(?:summary\s+)?report|export\s+(?:as\s+)?pdf", t):
        return {"type": "pdf_report"}

    return None