"""Phone automation over ADB, YouTube, and the BookMyShow booking flow."""

from config.settings import settings
from core.handlers.base import Reply, Request
from tools.web_automation import phone_actions as phone
from tools.web_automation.bookmyshow import open_bookmyshow, start_booking
from tools.web_automation.intent import detect_web_intent
from tools.web_automation.youtube import open_youtube, search_youtube

STOP_WORDS = {"stop automation", "abort booking", "stop booking"}

# intent type -> function(intent, context) -> str
ACTIONS = {
    "connect_phone_wifi": lambda i, c: phone.connect_phone_wifi(i["ip"]),
    "youtube_open": lambda i, c: open_youtube(),
    "youtube_search": lambda i, c: search_youtube(i.get("query") or _first(c, "recent_searches")),
    "spotify_open": lambda i, c: phone.open_spotify(),
    "spotify_search": lambda i, c: phone.spotify_search(i.get("query") or _first(c, "recent_searches")),
    "media_play_pause": lambda i, c: phone.play_pause_media(),
    "media_next": lambda i, c: phone.next_track(),
    "media_prev": lambda i, c: phone.previous_track(),
    "make_call": lambda i, c: phone.make_call(i.get("number") or _first(c, "recent_phone_numbers")),
    "dial": lambda i, c: phone.dial_number(i.get("number") or _first(c, "recent_phone_numbers")),
    "whatsapp_open": lambda i, c: phone.open_whatsapp(),
    "whatsapp_message": lambda i, c: phone.whatsapp_message(
        i.get("number") or _first(c, "recent_phone_numbers"), i.get("message", "")
    ),
    "maps_open": lambda i, c: phone.open_maps(),
    "navigate": lambda i, c: phone.navigate_to(i["destination"]),
    "maps_search": lambda i, c: phone.search_maps(i["query"]),
    "set_alarm": lambda i, c: phone.set_alarm(i["hour"], i["minute"]),
    "set_timer": lambda i, c: phone.set_timer(i["seconds"]),
    "mute": lambda i, c: phone.mute_phone(),
    "set_volume": lambda i, c: phone.set_volume_percent(i["percent"]),
    "volume_up": lambda i, c: phone.volume_up(i.get("steps", 1)),
    "volume_down": lambda i, c: phone.volume_down(i.get("steps", 1)),
    "set_brightness": lambda i, c: phone.set_brightness_percent(i["percent"]),
    "camera_open": lambda i, c: phone.open_camera(),
    "screenshot": lambda i, c: phone.take_screenshot(),
    "open_app": lambda i, c: phone.open_app(i["app"]),
    "bookmyshow_open": lambda i, c: open_bookmyshow(),
}

# Actions that run on the laptop browser rather than the phone.
_NO_ADB_NEEDED = {"youtube_open", "youtube_search", "bookmyshow_open"}


def _first(context: dict, key: str) -> str:
    values = context.get(key) or [""]
    return values[0]


def handle_stop(req: Request) -> Reply | None:
    if req.lower in STOP_WORDS:
        req.session.reset_booking()
        return Reply("Automation stopped.")
    return None


def handle_booking(req: Request) -> Reply | None:
    """Multi-step booking dialogue; captures input while active."""
    state = req.session.booking
    if not state.get("active"):
        return None
    data = state["data"]
    step = state["step"]

    if step == "city":
        data["city"] = req.text
        state["step"] = "date"
        return Reply("Which date?")
    if step == "date":
        data["date"] = req.text
        state["step"] = "time"
        return Reply("Preferred time?")
    if step == "time":
        data["time"] = req.text
        state["step"] = "confirm"
        return Reply(
            "Confirm booking:\n"
            f"Movie : {data.get('movie')}\nCity  : {data.get('city')}\n"
            f"Date  : {data.get('date')}\nTime  : {data.get('time')}\n\nReply YES or NO."
        )
    if step == "confirm":
        req.session.reset_booking()
        if req.lower == "yes":
            return Reply(start_booking(data["movie"], data["city"], data["date"], data["time"]))
        return Reply("Booking cancelled.")
    return None


def handle(req: Request) -> Reply | None:
    intent = detect_web_intent(req.text)
    if not intent:
        return None
    kind = intent["type"]

    if kind == "book_movie":
        req.session.booking = {
            "active": True,
            "type": "movie",
            "step": "city",
            "data": {"movie": intent["movie"]},
        }
        return Reply(f"Booking started for *{intent['movie']}*.\nWhich city?")

    action = ACTIONS.get(kind)
    if action is None:
        return None
    if not settings.ENABLE_PHONE_ADB and kind not in _NO_ADB_NEEDED:
        return Reply("Phone control is disabled (ENABLE_PHONE_ADB=false).")

    feature = "phone" if kind in {"make_call", "dial", "whatsapp_message"} else "web"
    context = req.session.memory.get_feature_context(feature)
    return Reply(action(intent, context))
