"""Slash-style commands that need no model."""

from core.handlers.base import STAGE_COMMAND, Reply, Request
from tools.location_tool import store_location

HELP_TEXT = (
    "*Orchestrix AI – Help*\n\n"
    "/api – cloud model (Gemini)\n"
    "/local – on-device model (Ollama)\n"
    "/web on | off\n"
    "/rag on | off\n"
    "/clearpdf\n"
    "/share_location – share your location for maps\n"
    "/agent <goal> – plan and chain several steps (asks before acting)\n\n"
    "*Everyday*\n"
    "• weather in Mumbai / forecast tomorrow\n"
    "• convert 500 USD to INR / TCS stock price / bitcoin price\n"
    "• summarize https://… / track price https://…\n"
    "• remind me to call mom at 6pm\n"
    "• find resume on drive\n\n"
    "*Google*\n"
    "• check my email / send email to a@b.com about …\n"
    "• add meeting tomorrow at 3pm / show my calendar\n"
    "• add task buy milk / show my tasks\n\n"
    "*Maps*\n"
    "• find restaurants nearby / directions to airport\n\n"
    "*Phone* (requires ADB):\n"
    "• open youtube / search youtube for <query>\n"
    "• play <song> on spotify\n"
    "• call <number> / whatsapp <number> <message>\n"
    "• set alarm for 7am / set timer for 5m\n"
    "• volume up / set brightness to 50%\n"
    "• connect phone <ip-address>\n\n"
    "Ask questions anytime."
)

SHARE_LOCATION_TEXT = (
    "To share your location:\n"
    "1. Tap the attachment icon in Telegram\n"
    "2. Select 'Location'\n"
    "3. Choose 'Send my current location'\n\n"
    "I'll use it for all location-based features."
)


def handle(req: Request) -> Reply | None:
    if req.lower == "/help":
        return Reply(HELP_TEXT, stage=STAGE_COMMAND)

    if req.lower == "/share_location":
        return Reply(SHARE_LOCATION_TEXT, stage=STAGE_COMMAND)

    if req.text.startswith("/location:"):
        parts = req.text.split(":")
        try:
            lat, lon = float(parts[1]), float(parts[2])
        except (IndexError, ValueError):
            return Reply("Could not read that location.", stage=STAGE_COMMAND)
        name = ":".join(parts[3:]) or "Current Location"
        store_location(req.user_id, lat, lon, name)
        return Reply(
            f"Location saved: {name}\n({lat:.4f}, {lon:.4f})\n\n"
            "Now I can help with:\n• Find restaurants nearby\n• Directions to places\n• Hotels around you",
            stage=STAGE_COMMAND,
        )

    return None
