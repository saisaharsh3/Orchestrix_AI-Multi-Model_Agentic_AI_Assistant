"""
utility_intent.py - Pattern detection for weather, finance, URLs, Drive,
reminders and PDF tools.

These features were routed by the Telegram bot before commit 6798188 and
were lost when routing moved into the orchestrator; they are restored here.
Task intents live in tools/google_tasks_intent.py.
"""

import re

CURRENCIES = {
    "USD", "INR", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD",
    "AED", "SAR", "HKD", "NZD", "KRW", "SEK", "NOK", "DKK", "ZAR", "RUB",
    "BRL", "MXN", "THB", "MYR", "IDR", "PHP", "PKR", "BDT", "LKR", "NPR",
}

CRYPTO_ALIASES = {
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL",
    "dogecoin": "DOGE", "doge": "DOGE",
    "xrp": "XRP", "cardano": "ADA", "ada": "ADA",
}

_NOT_TICKERS = {"THE", "MY", "GET", "SHOW", "CHECK", "WHAT", "IS", "A", "AN", "OF", "FOR", "CURRENT", "LIVE"}

_TIME = r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))"


def detect_utility_intent(text: str) -> dict | None:
    t = text.lower().strip()

    # ── URL (checked first: links contain words that match other patterns) ─
    url_match = re.search(r"https?://\S+", text)
    if url_match:
        url = url_match.group().rstrip(").,>")
        if re.search(r"track\s+(?:the\s+)?price|price\s+track|monitor\s+price", t):
            return {"type": "track_price", "url": url}
        if re.search(r"summar|explain|what is|tell me about|read|tl;?dr", t):
            return {"type": "summarize_url", "url": url}

    if re.search(r"\b(?:show|list|my)\s+tracked(?:\s+prices?)?\b|\btracked\s+prices?\b", t):
        return {"type": "show_tracked_prices"}

    # ── Weather ────────────────────────────────────────────────────────────
    if re.search(r"\b(?:weather|temperature|forecast|will it rain)\b", t):
        m = re.search(r"\b(?:in|at|for)\s+([a-z][a-z .'-]*?)(?:\s+(?:today|tomorrow|this week|now)|\?|$)", t)
        city = m.group(1).strip() if m else None
        is_forecast = bool(re.search(r"\b(?:tomorrow|forecast|week|next \d+ days)\b", t))
        return {"type": "weather_forecast" if is_forecast else "weather_current", "city": city}

    # ── Currency ───────────────────────────────────────────────────────────
    m = re.search(r"(?:convert\s+)?([\d,]+(?:\.\d+)?)\s*([a-z]{3})\s+(?:to|in|into)\s+([a-z]{3})\b", t)
    if m and m.group(2).upper() in CURRENCIES and m.group(3).upper() in CURRENCIES:
        return {
            "type": "currency_convert",
            "amount": float(m.group(1).replace(",", "")),
            "from_curr": m.group(2).upper(),
            "to_curr": m.group(3).upper(),
        }

    # ── Crypto (word boundaries: "sol" must not match "solve") ─────────────
    for alias, symbol in CRYPTO_ALIASES.items():
        if re.search(rf"\b{alias}\b", t) and re.search(r"\b(?:price|rate|worth|value|crypto|how much)\b", t):
            return {"type": "crypto_price", "symbol": symbol}

    # ── Stocks ─────────────────────────────────────────────────────────────
    m = (
        re.search(r"\b(?:share|stock)\s+price\s+of\s+([a-z0-9.&-]{1,15})\b", t)
        or re.search(r"\b([a-z0-9.&-]{1,15})\s+(?:stock|share)(?:\s+price)?\b", t)
        or re.search(r"\bstock\s+(?:price\s+)?(?:of\s+)?([a-z0-9.&-]{1,15})\b", t)
    )
    if m and m.group(1).upper() not in _NOT_TICKERS:
        return {"type": "stock_price", "ticker": m.group(1).upper()}

    # ── Google Drive ───────────────────────────────────────────────────────
    m = re.search(r"(?:find|search|look for)\s+(?:the\s+|my\s+)?(?:file\s+)?(.+?)\s+(?:in|on)\s+(?:google\s+|my\s+)?drive\b", t)
    if m:
        return {"type": "drive_search", "query": m.group(1).strip()}
    if re.search(r"\b(?:recent|latest)\s+(?:drive\s+)?(?:files?|documents?)\b|\bmy\s+drive\s+files?\b", t):
        return {"type": "drive_recent"}
    if re.search(r"\bfiles?\s+shared\s+with\s+me\b|\bshared\s+with\s+me\b", t):
        return {"type": "drive_shared"}

    # ── Reminders ──────────────────────────────────────────────────────────
    m = re.search(rf"remind\s+(?:me\s+)?(?:to\s+|about\s+)?(.+?)\s+(today|tomorrow)?\s*at\s+{_TIME}", t)
    if m:
        return {
            "type": "reminder_set",
            "message": m.group(1).strip(),
            "day": m.group(2) or "today",
            "time": m.group(3).strip(),
        }
    if re.search(r"\b(?:show|list|my)\s+reminders?\b", t):
        return {"type": "reminder_list"}
    m = re.search(r"cancel\s+(?:the\s+)?reminder\s+(?:for\s+|about\s+)?(.+)", t)
    if m:
        return {"type": "reminder_cancel", "keyword": m.group(1).strip()}

    # ── PDF compare / report ───────────────────────────────────────────────
    if re.search(r"compare\s+(?:the\s+)?(?:two\s+|both\s+)?pdfs?", t):
        return {"type": "pdf_compare"}
    if re.search(r"(?:generate|create|make)\s+(?:a\s+)?(?:pdf\s+)?(?:summary\s+)?report|export\s+(?:as\s+)?pdf", t):
        return {"type": "pdf_report"}

    return None
