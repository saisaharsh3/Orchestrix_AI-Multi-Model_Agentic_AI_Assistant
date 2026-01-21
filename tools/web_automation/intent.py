import re

# ============================================================
# WEB INTENT DETECTION
# ============================================================

def detect_web_intent(text: str) -> dict | None:
    """
    Detects deterministic web automation intents.
    Returns a structured intent dict or None.
    """

    t = text.lower().strip()

    # =========================
    # YouTube
    # =========================
    if re.search(r"\bopen\s+youtube\b", t):
        return {"type": "youtube_open"}

    yt_search = re.search(
        r"(open|search|play)\s+(?P<query>.+)\s+(on|in)\s+youtube",
        t
    )
    if yt_search:
        return {
            "type": "youtube_search",
            "query": yt_search.group("query").strip(),
        }

    # =========================
    # BookMyShow
    # =========================
    if re.search(r"\bopen\s+bookmyshow\b", t):
        return {"type": "bookmyshow_open"}

    book_movie = re.search(
        r"(book|buy)\s+(movie\s+)?tickets?\s+(for\s+)?(?P<movie>.+)",
        t
    )
    if book_movie:
        return {
            "type": "book_movie",
            "movie": book_movie.group("movie").strip(),
        }

    # =========================
    # No intent matched
    # =========================
    return None
