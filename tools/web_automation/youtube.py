"""
youtube.py — Phone-first YouTube automation via ADB
──────────────────────────────────────────────────────
Commands routed to the Android device that sent the Telegram message.
Falls back to laptop browser if no phone is connected.
"""

import urllib.parse
import webbrowser

from tools.web_automation.adb_manager import (
    is_phone_connected,
    shell,
    launch_intent,
    wake_screen,
)

# YouTube Android package
YT_PACKAGE = "com.google.android.youtube"
YT_ACTIVITY = "com.google.android.youtube/.HomeActivity"


# ── Helpers ───────────────────────────────────────────────────────────────

def _phone_open_youtube() -> str:
    wake_screen()
    r = launch_intent(
        action="android.intent.action.MAIN",
        package=YT_ACTIVITY,
    )
    if r.ok:
        return "▶️ YouTube opened on your phone."
    # fallback: try via monkey
    r2 = shell(f"monkey -p {YT_PACKAGE} -c android.intent.category.LAUNCHER 1")
    if r2.ok:
        return "▶️ YouTube opened on your phone."
    return f"❌ Could not open YouTube on phone: {r.error}"


def _phone_search_youtube(query: str) -> str:
    wake_screen()
    encoded = urllib.parse.quote(query)
    r = launch_intent(
        action="android.intent.action.SEARCH",
        package=f"{YT_PACKAGE}/.results.SearchActivity",
        extras={"query": query},
    )
    if r.ok:
        return f"🔍 Searching YouTube for '{query}' on your phone."

    # fallback: open search URL via browser intent
    url = f"https://www.youtube.com/results?search_query={encoded}"
    r2 = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=url,
    )
    if r2.ok:
        return f"🔍 YouTube search for '{query}' opened on your phone."
    return f"❌ YouTube search failed on phone: {r2.error}"


def _phone_play_youtube(video_id_or_url: str) -> str:
    """Play a specific YouTube video on phone."""
    wake_screen()
    if "youtube.com" in video_id_or_url or "youtu.be" in video_id_or_url:
        url = video_id_or_url
    else:
        url = f"https://www.youtube.com/watch?v={video_id_or_url}"

    r = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=url,
    )
    return "▶️ Playing video on your phone." if r.ok else f"❌ {r.error}"


def _laptop_open_youtube() -> str:
    url = "https://www.youtube.com"
    webbrowser.open(url)
    return (
        "📵 No phone connected — opened on laptop browser.\n"
        f"🔗 {url}"
    )


def _laptop_search_youtube(query: str) -> str:
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return (
        f"📵 No phone connected — opened on laptop browser.\n"
        f"🔗 {url}"
    )


# ── Public API ────────────────────────────────────────────────────────────

def open_youtube() -> str:
    if is_phone_connected():
        return _phone_open_youtube()
    return _laptop_open_youtube()


def search_youtube(query: str) -> str:
    if is_phone_connected():
        return _phone_search_youtube(query)
    return _laptop_search_youtube(query)


def play_youtube(video_id_or_url: str) -> str:
    if is_phone_connected():
        return _phone_play_youtube(video_id_or_url)
    webbrowser.open(video_id_or_url)
    return "▶️ Playing video in laptop browser."