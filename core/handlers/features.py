"""Tone, conversation history and maps."""

from core.handlers.base import Reply, Request
from core.model_manager import generate_llm
from core.prompt_builder import build_general_prompt
from core.rate_limiter import maps_limiter
from core.tone_controller import TONE_PROMPTS, is_valid_tone
from tools.feature_intent import CONFIDENCE_MEDIUM, detect_feature_intent
from tools.google_maps_tool import find_nearby, get_directions
from tools.google_maps_tool import search_maps as maps_search
from tools.location_tool import get_user_location

_PLACEHOLDERS = {"my location", "current location", "here", "my place"}
_NEED_LOCATION = "To use your location, share it first:\n/share_location"


def handle(req: Request) -> Reply | None:
    feat = detect_feature_intent(req.text)
    if not feat:
        return None
    kind = feat.get("type")
    confidence = feat.get("confidence")

    def reply(text: str) -> Reply:
        return Reply(text, confidence=confidence)

    if kind == "clarify":
        return reply(feat["message"])

    if kind == "set_tone":
        tone = feat["tone"]
        if not is_valid_tone(tone):
            return reply(f"Unknown tone. Available: {', '.join(TONE_PROMPTS)}")
        req.session.tone = tone
        return reply(f"Tone set to: {tone.upper()}")

    if kind == "search_history":
        return reply(req.session.memory.search_history(feat["query"]))

    if kind == "list_history":
        return reply(req.session.memory.list_history())

    if kind == "maps_search":
        maps_limiter.wait_if_needed("maps")
        return reply(maps_search(feat["query"]))

    if kind == "maps_directions":
        origin = _resolve_location(feat.get("origin"), req.user_id)
        destination = (feat.get("destination") or "").strip()
        if not origin:
            return reply(_NEED_LOCATION + "\n\nThen ask again for directions.")
        if not destination:
            return reply("Please tell me where you want to go.")
        maps_limiter.wait_if_needed("maps")
        result = get_directions(origin, destination, user_location_hint=_location_hint(req))
        if (confidence or 1.0) <= CONFIDENCE_MEDIUM:
            info = generate_llm(
                build_general_prompt(
                    f"How can I get to {destination}? What transportation options are available?",
                    [],
                    req.model_type,
                ),
                req.model_type,
            )
            result += f"\n\n📍 **General transport info:**\n\n{info}"
        return reply(result)

    if kind == "maps_nearby":
        location = _resolve_location("my location", req.user_id)
        if not location:
            return reply(_NEED_LOCATION)
        place_type = feat.get("place_type", "restaurants")
        maps_limiter.wait_if_needed("maps")
        result = find_nearby(place_type, location)
        if (confidence or 1.0) <= CONFIDENCE_MEDIUM:
            info = generate_llm(
                build_general_prompt(f"Tell me about {place_type} options in my area", [], req.model_type),
                req.model_type,
            )
            result += f"\n\n📝 **General info:**\n{info}"
        return reply(result)

    if kind == "maps_stops":
        from tools.google_maps_tool import find_stops_on_route

        origin = _resolve_location(feat.get("origin"), req.user_id)
        destination = (feat.get("destination") or "").strip()
        if not origin:
            return reply(_NEED_LOCATION)
        if not destination:
            return reply("Please specify your destination.")
        maps_limiter.wait_if_needed("maps")
        return reply(find_stops_on_route(origin, destination, feat.get("stop_type", "eating")))

    # Other types (e.g. "email_detected") are hints for later handlers.
    return None


def _resolve_location(location: str | None, user_id: str) -> str | None:
    """Turn "my location"/"here" into saved coordinates; pass other text through."""
    if location is None:
        return None
    location = location.strip().lower()
    if location in _PLACEHOLDERS:
        saved = get_user_location(user_id)
        return f"{saved['lat']},{saved['lon']}" if saved else None
    return location


def _location_hint(req: Request) -> str | None:
    saved = get_user_location(req.user_id)
    if saved and saved.get("name") not in (None, "", "Current Location"):
        return saved["name"]
    mentioned = req.session.memory.get_feature_context("maps").get("location", "")
    return mentioned.split()[-1] if mentioned else None
