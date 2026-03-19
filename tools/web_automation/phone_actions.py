"""
phone_actions.py — Daily phone automations via ADB
───────────────────────────────────────────────────
All actions target the Android phone connected via ADB (USB or Wi-Fi).
"""

import urllib.parse
import webbrowser

from tools.web_automation.adb_manager import (
    shell,
    launch_intent,
    wake_screen,
    set_volume,
    set_brightness,
    get_volume,
    get_brightness,
    is_phone_connected,
    ADBResult,
)


# ── Guard ─────────────────────────────────────────────────────────────────
def _require_phone() -> str | None:
    if not is_phone_connected():
        return (
            "❌ No Android phone connected.\n"
            "• USB  : Enable USB Debugging and plug in your phone.\n"
            "• Wi-Fi: Say 'connect phone <ip-address>' first."
        )
    return None


# ── Phone calls ───────────────────────────────────────────────────────────
def make_call(number: str) -> str:
    if err := _require_phone(): return err
    wake_screen()
    r = launch_intent(action="android.intent.action.CALL", data_uri=f"tel:{number}")
    return f"📞 Calling {number}..." if r.ok else f"❌ Call failed: {r.error}"


def dial_number(number: str) -> str:
    """Open dialer without auto-calling."""
    if err := _require_phone(): return err
    wake_screen()
    r = launch_intent(action="android.intent.action.DIAL", data_uri=f"tel:{number}")
    return f"📱 Dialer opened for {number}." if r.ok else f"❌ {r.error}"


# ── WhatsApp ──────────────────────────────────────────────────────────────
def open_whatsapp() -> str:
    if err := _require_phone(): return err
    wake_screen()
    r = shell("monkey -p com.whatsapp -c android.intent.category.LAUNCHER 1")
    return "💬 WhatsApp opened." if r.ok else f"❌ {r.error}"


def whatsapp_message(number: str, message: str) -> str:
    """
    Open WhatsApp chat with a pre-filled message.
    number: international format without '+', e.g. '919876543210'
    """
    if err := _require_phone(): return err
    wake_screen()
    encoded = urllib.parse.quote(message)
    url = f"https://api.whatsapp.com/send?phone={number}&text={encoded}"
    r = launch_intent(action="android.intent.action.VIEW", data_uri=url)
    return (
        f"💬 WhatsApp opened with message to {number}."
        if r.ok
        else f"❌ {r.error}"
    )


# ── Spotify ───────────────────────────────────────────────────────────────
def open_spotify() -> str:
    if err := _require_phone():
        url = "https://open.spotify.com"
        webbrowser.open(url)
        return f"📵 No phone connected — opened on laptop browser.\n🔗 {url}"
    wake_screen()
    r = shell("monkey -p com.spotify.music -c android.intent.category.LAUNCHER 1")
    return "🎵 Spotify opened on your phone." if r.ok else f"❌ {r.error}"


def spotify_search(query: str) -> str:
    encoded = urllib.parse.quote(query)
    if err := _require_phone():
        url = f"https://open.spotify.com/search/{encoded}"
        webbrowser.open(url)
        return f"📵 No phone connected — opened on laptop browser.\n🔗 {url}"
    wake_screen()
    r = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=f"spotify:search:{encoded}",
    )
    if r.ok:
        return f"🎵 Searching Spotify for '{query}'."
    r2 = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=f"https://open.spotify.com/search/{encoded}",
    )
    return f"🎵 Spotify search opened." if r2.ok else f"❌ {r2.error}"


def play_pause_media() -> str:
    if err := _require_phone(): return err
    r = shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")
    return "⏯️ Play/Pause toggled." if r.ok else f"❌ {r.error}"


def next_track() -> str:
    if err := _require_phone(): return err
    shell("input keyevent KEYCODE_MEDIA_NEXT")
    return "⏭️ Next track."


def previous_track() -> str:
    if err := _require_phone(): return err
    shell("input keyevent KEYCODE_MEDIA_PREVIOUS")
    return "⏮️ Previous track."


# ── Google Maps ───────────────────────────────────────────────────────────
def open_maps() -> str:
    if err := _require_phone():
        url = "https://maps.google.com"
        webbrowser.open(url)
        return f"📵 No phone connected — opened on laptop browser.\n🔗 {url}"
    wake_screen()
    r = shell("monkey -p com.google.android.apps.maps -c android.intent.category.LAUNCHER 1")
    return "🗺️ Google Maps opened." if r.ok else f"❌ {r.error}"


def navigate_to(destination: str) -> str:
    encoded = urllib.parse.quote(destination)
    if err := _require_phone():
        url = f"https://maps.google.com/?q={encoded}"
        webbrowser.open(url)
        return f"📵 No phone connected — opened on laptop browser.\n🔗 {url}"
    wake_screen()
    r = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=f"google.navigation:q={encoded}",
        package="com.google.android.apps.maps/com.google.android.maps.MapsActivity",
    )
    if r.ok:
        return f"🧭 Navigation started to '{destination}'."
    r2 = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=f"https://maps.google.com/?q={encoded}",
    )
    return f"🧭 Maps opened for '{destination}'." if r2.ok else f"❌ {r2.error}"


def search_maps(query: str) -> str:
    encoded = urllib.parse.quote(query)
    if err := _require_phone():
        url = f"https://maps.google.com/?q={encoded}"
        webbrowser.open(url)
        return f"📵 No phone connected — opened on laptop browser.\n🔗 {url}"
    wake_screen()
    r = launch_intent(
        action="android.intent.action.VIEW",
        data_uri=f"geo:0,0?q={encoded}",
    )
    return f"📍 Maps search for '{query}' opened." if r.ok else f"❌ {r.error}"


# ── Alarm & Timer ─────────────────────────────────────────────────────────
def set_alarm(hour: int, minute: int, message: str = "") -> str:
    if err := _require_phone(): return err
    wake_screen()
    cmd = (
        f"am start -a android.intent.action.SET_ALARM "
        f"--ei android.intent.extra.alarm.HOUR {hour} "
        f"--ei android.intent.extra.alarm.MINUTES {minute} "
        f"--ez android.intent.extra.alarm.SKIP_UI true"
    )
    if message:
        cmd += f" --es android.intent.extra.alarm.MESSAGE '{message}'"
    r = shell(cmd)
    time_str = f"{hour:02d}:{minute:02d}"
    return f"⏰ Alarm set for {time_str}." if r.ok else f"❌ Alarm failed: {r.error}"


def set_timer(seconds: int, message: str = "") -> str:
    if err := _require_phone(): return err
    wake_screen()
    cmd = (
        f"am start -a android.intent.action.SET_TIMER "
        f"--ei android.intent.extra.alarm.LENGTH {seconds} "
        f"--ez android.intent.extra.alarm.SKIP_UI true"
    )
    if message:
        cmd += f" --es android.intent.extra.alarm.MESSAGE '{message}'"
    r = shell(cmd)
    mins, secs = divmod(seconds, 60)
    label = f"{mins}m {secs}s" if mins else f"{secs}s"
    return f"⏱️ Timer set for {label}." if r.ok else f"❌ Timer failed: {r.error}"


# ── Volume ────────────────────────────────────────────────────────────────
def volume_up(steps: int = 1) -> str:
    if err := _require_phone(): return err
    for _ in range(steps):
        shell("input keyevent KEYCODE_VOLUME_UP")
    return f"🔊 Volume up ({steps} step{'s' if steps > 1 else ''})."


def volume_down(steps: int = 1) -> str:
    if err := _require_phone(): return err
    for _ in range(steps):
        shell("input keyevent KEYCODE_VOLUME_DOWN")
    return f"🔉 Volume down ({steps} step{'s' if steps > 1 else ''})."


def set_volume_percent(percent: int) -> str:
    if err := _require_phone(): return err
    r = set_volume(percent)
    return f"🔊 Volume set to {percent}%." if r.ok else f"❌ {r.error}"


def mute_phone() -> str:
    if err := _require_phone(): return err
    shell("input keyevent KEYCODE_VOLUME_MUTE")
    return "🔇 Phone muted."


# ── Brightness ────────────────────────────────────────────────────────────
def set_brightness_percent(percent: int) -> str:
    if err := _require_phone(): return err
    level = int(percent / 100 * 255)
    r = set_brightness(level)
    return f"☀️ Brightness set to {percent}%." if r.ok else f"❌ {r.error}"


# ── Camera ────────────────────────────────────────────────────────────────
def open_camera() -> str:
    if err := _require_phone(): return err
    wake_screen()
    r = launch_intent(
        action="android.media.action.STILL_IMAGE_CAMERA",
    )
    return "📷 Camera opened." if r.ok else f"❌ {r.error}"


def take_screenshot() -> str:
    if err := _require_phone(): return err
    r = shell("screencap -p /sdcard/screenshot.png")
    return "📸 Screenshot saved to /sdcard/screenshot.png." if r.ok else f"❌ {r.error}"


# ── General app launcher ──────────────────────────────────────────────────
APP_PACKAGES = {
    "chrome":    "com.android.chrome",
    "gmail":     "com.google.android.gm",
    "instagram": "com.instagram.android",
    "twitter":   "com.twitter.android",
    "x":         "com.twitter.android",
    "facebook":  "com.facebook.katana",
    "telegram":  "org.telegram.messenger",
    "maps":      "com.google.android.apps.maps",
    "spotify":   "com.spotify.music",
    "whatsapp":  "com.whatsapp",
    "youtube":   "com.google.android.youtube",
    "settings":  "com.android.settings",
    "calculator":"com.google.android.calculator",
    "clock":     "com.google.android.deskclock",
    "files":     "com.google.android.apps.nbu.files",
    "photos":    "com.google.android.apps.photos",
}


def open_app(app_name: str) -> str:
    if err := _require_phone(): return err
    wake_screen()
    pkg = APP_PACKAGES.get(app_name.lower())
    if not pkg:
        return f"❓ Unknown app '{app_name}'. Try: {', '.join(APP_PACKAGES.keys())}"
    r = shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
    return f"📱 {app_name.capitalize()} opened." if r.ok else f"❌ {r.error}"


# ── Wi-Fi ADB connector ───────────────────────────────────────────────────
def connect_phone_wifi(ip: str) -> str:
    from tools.web_automation.adb_manager import connect_wifi
    r = connect_wifi(ip)
    return f"🔗 Connected to phone at {ip}." if r.ok else f"❌ {r.error}"