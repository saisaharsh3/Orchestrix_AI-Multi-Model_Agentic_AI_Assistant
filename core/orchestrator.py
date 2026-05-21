import re
from datetime import datetime
import uuid
import time
import json
from pathlib import Path

# ✅ NEW: Logging, Rate Limiting, Settings
from core.logger import get_logger
from core.rate_limiter import with_rate_limit, with_retry, gemini_limiter, web_limiter, maps_limiter
from config.settings import settings, UserPreferences

logger = get_logger(__name__)

# ✅ RESEARCH INSTRUMENTATION: Setup trace logging
LOGS_DIR = Path("research/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
TRACE_FILE = LOGS_DIR / "orchestration_trace.jsonl"

def log_orchestration_event(event: dict) -> None:
    """Log orchestration trace event to JSONL file for research analysis."""
    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.debug(f"Failed to log orchestration event: {e}")

from core.model_manager import generate_llm
from core.prompt_builder import build_rag_prompt, build_general_prompt, build_web_prompt
from core.stylometric_defense import StyleometricDefense  # ✅ NEW: Experiment 5 defense
from tools.web_search import web_search
from tools.wiki_search import wiki_search
from tools.news_search import news_search
from core.tone_controller import tone_controller
from core.conversation_memory import conversation_memory
from tools.smart_search import smart_search
from tools.google_maps_tool import search_maps as maps_search, get_directions, find_nearby
from tools.feature_intent import detect_feature_intent
from tools.location_tool import get_user_location, store_location, load_user_locations

from tools.email_intent import detect_email_intent, extract_email_fields, build_email_body
from tools.email_tool import (
    send_email, save_draft, read_inbox, format_inbox,
    reply_to_email, forward_email, search_emails,
)
from tools.calendar_intent import detect_calendar_intent, extract_event_fields
from tools.calendar_tool import (
    add_event, quick_add_event, list_events,
    delete_event, parse_event_datetime,
)
from tools.google_tasks_tool import (
    list_tasks, add_task, complete_task, delete_task
)

from tools.web_automation.intent import detect_web_intent
from tools.web_automation.planner import WEB_STATE, reset_web_state
from tools.web_automation.youtube import open_youtube, search_youtube, play_youtube
from tools.web_automation.bookmyshow import open_bookmyshow, start_booking
from tools.web_automation.phone_actions import (
    make_call, dial_number,
    open_whatsapp, whatsapp_message,
    open_spotify, spotify_search,
    play_pause_media, next_track, previous_track,
    open_maps, navigate_to, search_maps,
    set_alarm, set_timer,
    volume_up, volume_down, set_volume_percent, mute_phone,
    set_brightness_percent,
    open_camera, take_screenshot,
    open_app, connect_phone_wifi,
)
from core.smart_intent_detector import detect_intent_with_llm

# ✅ INITIALIZATION: Load locations at startup
load_user_locations()

# ✅ CONFIDENCE THRESHOLDS for smart ambiguity detection
CONFIDENCE_HIGH = 0.9      # Very sure of intent
CONFIDENCE_MEDIUM = 0.6    # Fairly sure, might be ambiguous  
CONFIDENCE_LOW = 0.3       # Very ambiguous, ask user or provide both


# ✅ NEW: Consent-based fallback handler (Experiment 4 privacy boundary)
def execute_llm_with_fallback(
    prompt: str,
    model_type: str,
    query: str,
    user_id: str = None,
    trace: dict = None
) -> str:
    """
    Execute LLM generation with consent-based fallback for local model failures.

    Maintains the Experiment 4 zero-disclosure guarantee by requiring explicit
    user consent before switching from local to API mode.

    Args:
        prompt: The prompt to send to LLM
        model_type: "local" or "api"
        query: Original user query (for fallback consent message)
        user_id: User ID for preferences and logging
        trace: Trace dict for research instrumentation

    Returns:
        LLM response text

    Behavior:
        ✅ If local model works: Return response
        ❌ If local model crashes: Show consent dialog instead of failing silently
        After consent:
            - User chooses: Retry local, Fallback to API, or Cancel
        Zero-disclosure guarantee:
            - Only broken if user explicitly consents to API fallback
    """

    try:
        # Try local model if requested
        if model_type == "local":
            try:
                response = generate_llm(prompt, "local")
                logger.info(f"Local LLM succeeded", extra={"user_id": user_id})
                if trace:
                    trace["local_success"] = True
                return response

            except Exception as e:
                # Local model failed - show consent dialog
                logger.warning(
                    f"Local model failed: {str(e)[:100]}",
                    extra={"user_id": user_id, "error": str(e)},
                )

                if trace:
                    trace["local_failed"] = True
                    trace["fallback_dialog_shown"] = True

                # ✅ PRIVACY BOUNDARY: Ask for explicit consent before using API
                consent_response = show_privacy_boundary_consent(
                    error_type="LOCAL_MODEL_CRASHED",
                    query=query,
                    user_id=user_id,
                )

                # Handle user choice
                if consent_response["action"] == "retry_local":
                    logger.info(
                        f"User chose: retry local",
                        extra={"user_id": user_id},
                    )
                    # Wait 5 seconds and retry
                    time.sleep(5)
                    return execute_llm_with_fallback(
                        prompt, "local", query, user_id, trace
                    )

                elif consent_response["action"] == "fallback_to_api":
                    logger.info(
                        f"User approved API fallback (explicit consent)",
                        extra={"user_id": user_id},
                    )
                    if trace:
                        trace["user_consented_to_api"] = True
                    response = generate_llm(prompt, "api")
                    return f"[⚠️ Switched to API temporarily due to local model error]\n\n{response}"

                else:  # cancel
                    logger.info(
                        f"User cancelled query after local model failure",
                        extra={"user_id": user_id},
                    )
                    if trace:
                        trace["user_cancelled"] = True
                    return "❌ Query cancelled. Your local model is not responding. Try again in a moment."

        else:
            # API mode - just call it directly
            try:
                response = generate_llm(prompt, "api")
                logger.info(f"API model succeeded", extra={"user_id": user_id})
                return response
            except Exception as e:
                # ✅ NEW: If API fails (quota exceeded, etc), fallback to local model
                error_msg = str(e).lower()
                if "quota" in error_msg or "resource_exhausted" in error_msg or "429" in error_msg:
                    logger.warning(
                        f"API quota exceeded, falling back to local model",
                        extra={"user_id": user_id},
                    )
                    try:
                        response = generate_llm(prompt, "local")
                        return f"[Using local model due to API quota limit]\n\n{response}"
                    except Exception as local_error:
                        logger.error(f"Local fallback also failed: {local_error}")
                        raise
                else:
                    raise

    except Exception as e:
        # Unexpected error
        logger.error(
            f"Unexpected error in LLM execution: {str(e)[:200]}",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        return f"❌ Error: {str(e)[:100]}. Please try again."


def show_privacy_boundary_consent(
    error_type: str,
    query: str,
    user_id: str = None
) -> dict:
    """
    Show user consent dialog for privacy boundary violation.

    This maintains the Experiment 4 zero-disclosure guarantee by requiring
    explicit user consent before breaking the local-only privacy contract.

    Args:
        error_type: "LOCAL_MODEL_CRASHED", "OUT_OF_MEMORY", etc.
        query: The query that caused the error
        user_id: User ID for logging

    Returns:
        {
            "action": "retry_local" | "fallback_to_api" | "cancel",
            "timestamp": ISO timestamp,
            "user_id": user_id
        }

    UI Display (in actual client):
        ┌─────────────────────────────────────────────────────────┐
        │ ⚠️ Local Model Error                                    │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │ Your local (private) model ran out of memory.         │
        │ Your query stays private on your device by default.   │
        │                                                         │
        │ What do you want to do?                               │
        │                                                         │
        │ [⏳ Wait & Retry] Keep it private (may take time)    │
        │ [🌐 Send to API] Process on Google servers (seen)    │
        │ [❌ Cancel]      Don't send the query                │
        │                                                         │
        │ Privacy note: Per our ToS, API queries retained 30d. │
        └─────────────────────────────────────────────────────────┘
    """

    # ✅ NOTE: In production, this would show an interactive dialog
    # For now, we log the consent and return a default choice

    logger.info(
        f"Privacy boundary consent dialog triggered: {error_type}",
        extra={"user_id": user_id, "error_type": error_type},
    )

    # In a real implementation, this would:
    # 1. Pause orchestration
    # 2. Show UI dialog to user
    # 3. Wait for user input
    # 4. Return the choice

    # For MVP, default to retry_local (safest choice)
    logger.warning(
        f"Privacy boundary: Using default behavior (retry_local). "
        f"Production should show interactive dialog.",
        extra={"user_id": user_id},
    )

    return {
        "action": "retry_local",  # Default: retry without breaking privacy
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "error_type": error_type,
    }


def is_fact_question(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in (
        "who is", "current", "cm of", "chief minister",
        "prime minister", "president",
    ))


EMAIL_STATE = {
    "pending":  False,
    "action":   "send",
    "to":       "",
    "subject":  "",
    "body":     "",
    "tone":     "professional",
    "msg_id":   "",
    "use_ai":   False,
    "original_input": "",
}

CALENDAR_STATE = {
    "pending":  False,
    "title":    "",
    "start":    None,
    "end":      None,
    "location": "",
}


def get_feature_context(feature: str) -> dict:
    """
    Helper to get relevant context for any feature from conversation history.
    
    Args:
        feature: One of "maps", "email", "calendar", "phone", "web", "weather", "finance", "news"
    
    Returns:
        Dict with context specific to the feature
    """
    return conversation_memory.get_feature_context(feature, max_turns=15)


def generate_response(
    user_input: str,
    model_type: str = "api",
    pdf_store=None,
    use_web: bool = True,
    use_pdf: bool = False,
    user_id: str = None,
) -> str:

    # ✅ RESEARCH INSTRUMENTATION: Initialize trace tracking
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    trace = {
        "request_id": request_id,
        "timestamp": start_time,
        "input": user_input[:100],  # First 100 chars only
        "stage_reached": None,
        "stages_executed": [],
        "total_latency_ms": 0,
        "confidence": None,
        "model_type": model_type,
    }
    
    today = datetime.now().strftime("%B %d, %Y")
    user_input = user_input.strip()
    user_lower = user_input.lower()
    context_blocks = []
    
    # ✅ NEW: Log the request
    logger.info(f"Processing request", extra={
        "user_id": user_id,
        "input_length": len(user_input),
        "model": model_type,
        "features": f"web={use_web}, pdf={use_pdf}"
    })
    
    # ✅ NEW: Load user preferences if user_id provided
    if user_id:
        try:
            user_prefs = UserPreferences.get_user_prefs(user_id)
            model_type = user_prefs.get("preferred_model", model_type)
            logger.debug(f"Using user preference: model={model_type}", extra={"user_id": user_id})
        except Exception as e:
            logger.warning(f"Failed to load user preferences: {e}", extra={"user_id": user_id})

    # ── /help ──────────────────────────────────────────────────────────────
    if user_lower == "/help":
        result = (
            " *Orchestrix AI – Help*\n\n"
            "/api – API model\n"
            "/local – Local model\n"
            "/web on | off\n"
            "/rag on | off\n"
            "/clearpdf\n"
            "/share_location – Share your location for maps\n\n"
            " *Maps Commands*\n"
            "• find restaurants nearby\n"
            "• directions to airport\n"
            "• hotels near me\n\n"
            " *Phone Commands* (requires ADB):\n"
            "• open youtube / search youtube for <query>\n"
            "• open spotify / play <song> on spotify\n"
            "• call <number> / dial <number>\n"
            "• whatsapp <number> <message>\n"
            "• navigate to <place> / search maps <place>\n"
            "• set alarm for HH:MM / set timer for Xm Ys\n"
            "• volume up/down / set volume to X%\n"
            "• set brightness to X%\n"
            "• open camera / take screenshot\n"
            "• open <app-name>\n"
            "• connect phone <ip-address>\n\n"
            "Ask questions anytime."
        )
        conversation_memory.add_turn(user_input, result)
        # ✅ RESEARCH: Log trace before returning
        trace["stage_reached"] = 0
        trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
        log_orchestration_event(trace)
        return result

    # ── Location sharing cmd ───────────────────────────────────────────────
    if user_lower == "/share_location":
        result = (
            " To share your location:\n"
            "1. Click the attachment icon (+) in Telegram\n"
            "2. Select 'Location'\n"
            "3. Choose 'Send your current location'\n\n"
            "I'll save it for all location-based features!"
        )
        conversation_memory.add_turn(user_input, result)
        # ✅ RESEARCH: Log trace before returning
        trace["stage_reached"] = 0
        trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
        log_orchestration_event(trace)
        return result

    # ── Location handling (when location is received) ─────────────────────
    if user_input.startswith("/location:"):
        try:
            parts = user_input.split(":")
            if len(parts) >= 4:
                lat = float(parts[1])
                lon = float(parts[2])
                place_name = ":".join(parts[3:]) or "Current Location"
                
                store_location(user_id, lat, lon, place_name)
                result = f" Location saved: {place_name}\n({lat:.4f}, {lon:.4f})\n\nNow I can help with:\n• Find restaurants nearby\n• Directions to places\n• Hotels around you"
                conversation_memory.add_turn(user_input, result)
                return result
        except Exception as e:
            result = f" Error saving location: {str(e)}"
            conversation_memory.add_turn(user_input, result)
            return result

    # ── Stop automation ────────────────────────────────────────────────────
    if user_lower in {"stop automation", "abort booking", "stop booking"}:
        reset_web_state()
        result = " Automation stopped."
        conversation_memory.add_turn(user_input, result)
        return result

    # ── Email confirmation flow ────────────────────────────────────────────
    if EMAIL_STATE["pending"]:
        if user_lower in {"yes", "send", "confirm"}:
            action = EMAIL_STATE["action"]
            if action == "draft":
                result = save_draft(EMAIL_STATE["to"], EMAIL_STATE["subject"], EMAIL_STATE["body"])
            elif action == "reply":
                result = reply_to_email(EMAIL_STATE["msg_id"], EMAIL_STATE["body"])
            elif action == "forward":
                result = forward_email(EMAIL_STATE["msg_id"], EMAIL_STATE["to"])
            else:
                result = send_email(EMAIL_STATE["to"], EMAIL_STATE["subject"], EMAIL_STATE["body"])
            EMAIL_STATE["pending"] = False
            conversation_memory.add_turn(user_input, result)
            return result

        if user_lower in {"no", "cancel"}:
            EMAIL_STATE["pending"] = False
            result = " Email cancelled."
            conversation_memory.add_turn(user_input, result)
            return result
        
        # 🔄 Handle email regeneration requests (with optional context)
        regen_keywords = {"regenerate", "again", "different", "retry", "new", "again please", "try again", "regen"}
        has_regen = any(keyword in user_lower for keyword in regen_keywords)
        
        if has_regen:
            if EMAIL_STATE.get("use_ai"):
                # Extract additional context after regenerate keyword
                # Sort by length (longest first) to avoid matching shorter keywords first
                sorted_keywords = sorted(regen_keywords, key=len, reverse=True)
                additional_context = None
                for keyword in sorted_keywords:
                    if keyword in user_lower:
                        # Find where the keyword is and extract text after it
                        idx = user_lower.find(keyword)
                        after_keyword = user_input[idx + len(keyword):].strip()
                        # Remove common separators
                        after_keyword = after_keyword.lstrip(" -:.,").strip()
                        if after_keyword:
                            additional_context = after_keyword
                        break
                
                # Build enhanced prompt with additional instructions
                if additional_context and additional_context.lower() not in regen_keywords and len(additional_context) > 2:
                    # User provided specific guidance
                    enhanced_prompt = f"""
Subject hint: {EMAIL_STATE["subject"] or "Email"}
User instruction: {EMAIL_STATE["subject"] or "Professional email"}
Tone: {EMAIL_STATE["tone"]}
Additional feedback/context: {additional_context}

Write a complete, ready-to-send email body incorporating the additional feedback. 
Make sure to address the user's specific request. No subject line, no placeholders.
Just the body text starting with a greeting and ending with a sign-off.
""".strip()
                else:
                    # Just regenerate without specific guidance
                    enhanced_prompt = build_email_body(
                        EMAIL_STATE["subject"] or "Email",
                        EMAIL_STATE["subject"] or "Professional email",
                        EMAIL_STATE["tone"]
                    )
                
                EMAIL_STATE["body"] = generate_llm(enhanced_prompt, "api")
                
                feedback_note = f"\n📝 Feedback applied: {additional_context}" if additional_context and additional_context.lower() not in regen_keywords else ""
                result = (
                    " 🔄 New email generated:{feedback}\n\n"
                    f"To     : {EMAIL_STATE['to']}\n"
                    f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
                    f"{EMAIL_STATE['body']}\n\n"
                    "Reply YES to send, NO to cancel, or REGENERATE with more feedback for another version."
                ).format(feedback=feedback_note)
                conversation_memory.add_turn(user_input, result)
                return result
            else:
                result = " ℹ️ Regeneration only works with AI-generated emails. Try: 'send email to [recipient] use ai [topic]'"
                conversation_memory.add_turn(user_input, result)
                return result

        return (
            " Pending confirmation:\n\n"
            f"Action : {EMAIL_STATE['action'].upper()}\n"
            f"To     : {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            "Reply YES to confirm, NO to cancel, or REGENERATE for a new version."
        )

    # ── Calendar confirmation flow ─────────────────────────────────────────
    if CALENDAR_STATE["pending"]:
        if user_lower in {"yes", "confirm", "add it", "ok"}:
            from datetime import timedelta
            start = CALENDAR_STATE["start"]
            end   = CALENDAR_STATE["end"] or (start + timedelta(hours=1) if start else None)
            result = add_event(
                title=CALENDAR_STATE["title"],
                start=start,
                end=end,
                location=CALENDAR_STATE["location"],
            )
            CALENDAR_STATE["pending"] = False
            conversation_memory.add_turn(user_input, result)
            return result

        if user_lower in {"no", "cancel"}:
            CALENDAR_STATE["pending"] = False
            result = " Event cancelled."
            conversation_memory.add_turn(user_input, result)
            return result

        return (
            " Pending calendar event:\n\n"
            f"Title   : {CALENDAR_STATE['title']}\n"
            f"Time    : {CALENDAR_STATE['start'].strftime('%b %d, %Y %I:%M %p') if CALENDAR_STATE['start'] else 'TBD'}\n"
            + (f"Location: {CALENDAR_STATE['location']}\n" if CALENDAR_STATE['location'] else "")
            + "\nReply YES to add or NO to cancel."
        )

    # ── FEATURE INTENT: Tone, Search, History, Maps ────────────────────────
    feat = detect_feature_intent(user_input)
    if feat:
        t = feat.get("type")
        
        if t == "clarify":
            msg = feat["message"]
            # ✅ Log clarification requests
            conversation_memory.add_turn(user_input, msg)
            return msg
        
        if t == "set_tone":
            result = tone_controller.set_tone(feat["tone"])
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "smart_search":
            result = smart_search(feat["query"])
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "search_history":
            result = conversation_memory.search_history(feat["query"])
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "list_history":
            result = conversation_memory.list_history()
            conversation_memory.add_turn(user_input, result)
            return result
        
        # ✅ MAPS FEATURES - Check location first, then execute
        if t == "maps_search":
            result = maps_search(feat["query"])
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "maps_directions":
            # 🗺️ Get location context from conversation history
            maps_context = get_feature_context("maps")
            
            origin_str = _resolve_location_string(feat.get("origin"), user_id)
            destination = feat.get("destination", "").strip()
            confidence = feat.get("confidence", 1.0)
            
            # Extract location hint from saved location or conversation
            location_hint = None
            if user_id:
                user_loc = get_user_location(user_id)
                if user_loc and "name" in user_loc:
                    location_name = user_loc.get("name", "")
                    if location_name and location_name != "Current Location":
                        location_hint = location_name
            
            # If no location hint from user location, try conversation context
            if not location_hint and maps_context.get("location"):
                location_hint = maps_context["location"].split()[-1] if maps_context["location"] else None
            
            if not origin_str:
                result = (
                    " To get directions from your location, please share it:\n"
                    "/share_location\n\n"
                    "Then ask again for directions."
                )
            elif not destination:
                result = " Please specify where you want to go."
            else:
                # ✅ Pass location hint to improve search accuracy
                maps_result = get_directions(origin_str, destination, user_location_hint=location_hint)
                
                # ✅ SECONDARY: If confidence is LOW/MEDIUM, also provide general info
                if confidence <= CONFIDENCE_MEDIUM:
                    info_prompt = build_general_prompt(
                        f"How can I get to {destination}? What are the transportation options available?",
                        [],
                        model_type
                    )
                    info_result = generate_llm(info_prompt, model_type)
                    
                    result = (
                        f"{maps_result}\n\n"
                        f"📍 **Also, here's general info about transportation:**\n\n"
                        f"{info_result}"
                    )
                else:
                    result = maps_result
            
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "maps_nearby":
            location_str = _resolve_location_string("my location", user_id)
            confidence = feat.get("confidence", 1.0)
            
            if not location_str:
                result = (
                    " To find places nearby, please share your location:\n"
                    "/share_location"
                )
            else:
                result = find_nearby(feat.get("place_type", "restaurants"), location_str)
                
                # If confidence is low, also provide general info
                if confidence <= CONFIDENCE_MEDIUM:
                    place_type = feat.get("place_type", "restaurants")
                    info_prompt = build_general_prompt(
                        f"Tell me about {place_type} options in my area",
                        [],
                        model_type
                    )
                    info_result = generate_llm(info_prompt, model_type)
                    result = f"{result}\n\n📝 **General info:**\n{info_result}"
            
            conversation_memory.add_turn(user_input, result)
            return result
        
        if t == "maps_stops":
            origin_str = _resolve_location_string(feat.get("origin"), user_id)
            destination = feat.get("destination", "").strip()
            stop_type = feat.get("stop_type", "eating")
            
            if not origin_str:
                result = (
                    " To find stops along your route, please share your location:\n"
                    "/share_location\n\n"
                    "Then ask: 'eating stops from my location to {destination}'"
                )
            elif not destination:
                result = " Please specify your destination."
            else:
                from tools.google_maps_tool import find_stops_on_route
                result = find_stops_on_route(origin_str, destination, stop_type)
            conversation_memory.add_turn(user_input, result)
            return result

    # ── Read inbox (no confirmation needed) ───────────────────────────────
    email_intent = detect_email_intent(user_input)

    if email_intent == "read":
        emails = read_inbox(max_results=5, unread_only=True)
        result = format_inbox(emails)
        conversation_memory.add_turn(user_input, result)
        return result

    if email_intent == "send" and re.search(r"search|find|look for", user_lower):
        m = re.search(r"(?:search|find|look for)\s+(?:email[s]?\s+(?:about|from|for)\s+)?(.+)", user_lower)
        query = m.group(1).strip() if m else user_input
        result = search_emails(query)
        conversation_memory.add_turn(user_input, result)
        return result

    if email_intent in {"send", "draft", "reply", "forward"}:
        # 📧 Get email context from conversation history
        email_context = get_feature_context("email")
        
        extracted = extract_email_fields(user_input)
        
        # If recipient not found, try to extract from recent emails
        if not extracted.get("to") and email_context.get("recent_recipients"):
            extracted["to"] = email_context["recent_recipients"][0]
        
        # Use recent tone if detected
        if email_context.get("email_tone"):
            extracted["tone"] = email_context["email_tone"]
        
        missing   = extracted.get("missing", [])
        if missing:
            result = " Please provide: " + ", ".join(missing)
            conversation_memory.add_turn(user_input, result)
            return result

        body = extracted.get("body") or ""
        use_ai = extracted.get("use_ai", False)
        
        # If 'use ai' keyword detected, always generate content via LLM
        if use_ai:
            prompt = build_email_body(
                extracted.get("subject") or "Email",
                body or extracted.get("subject") or "Professional email",
                extracted.get("tone", "professional")
            )
            body = generate_llm(prompt, "api")
        # Or if body is short (<8 words) and has subject, generate professionally
        elif len(body.split()) < 8 and extracted.get("subject"):
            prompt = build_email_body(extracted["subject"], body or extracted["subject"], extracted.get("tone", "professional"))
            body = generate_llm(prompt, "api")
        # Or if no body but has subject, use subject as body
        elif not body and extracted.get("subject"):
            body = extracted["subject"]

        EMAIL_STATE.update(
            pending=True,
            action=email_intent,
            to=extracted["to"] or "",
            subject=extracted.get("subject") or "",
            body=body,
            tone=extracted.get("tone", "professional"),
            use_ai=use_ai,
            original_input=user_input,
        )
        regenerate_hint = " REGENERATE or REGENERATE [feedback] for a new version." if use_ai else ""
        return (
            f" Confirm {email_intent.upper()}:\n\n"
            f"To     : {EMAIL_STATE['to']}\n"
            f"Subject: {EMAIL_STATE['subject'] or '(no subject)'}\n\n"
            f"{EMAIL_STATE['body']}\n\n"
            f"Reply YES to send or NO to cancel.{regenerate_hint}"
        )

    # ── Calendar intent ────────────────────────────────────────────────────
    cal_intent = detect_calendar_intent(user_input)

    if cal_intent == "list":
        result = list_events(days_ahead=7)
        conversation_memory.add_turn(user_input, result)
        return result

    if cal_intent == "delete":
        m = re.search(r"(?:delete|remove|cancel)\s+(?:event\s+)?(.+?)(?:\s+from\s+calendar)?$", user_lower)
        title = m.group(1).strip() if m else user_input
        result = delete_event(title)
        conversation_memory.add_turn(user_input, result)
        return result

    if cal_intent == "quick_add":
        result = quick_add_event(user_input)
        conversation_memory.add_turn(user_input, result)
        return result

    if cal_intent == "add":
        # 📅 Get calendar context from conversation history
        cal_context = get_feature_context("calendar")
        
        fields = extract_event_fields(user_input)
        start  = parse_event_datetime(user_input)
        
        # If no start time found, check recent conversation for time mentions
        if not start and cal_context.get("recent_dates"):
            # Try to extract time from recent mentions
            pass  # parse_event_datetime already uses intelligent parsing
        
        from datetime import timedelta
        end = start + timedelta(hours=fields.get("duration_hr", 1)) if start else None

        CALENDAR_STATE.update(
            pending=True,
            title=fields["title"],
            start=start,
            end=end,
            location=fields.get("location", ""),
        )
        return (
            f" Add to Google Calendar?\n\n"
            f"*{CALENDAR_STATE['title']}*\n"
            f" {start.strftime('%b %d, %Y %I:%M %p') if start else 'Time unknown'}\n"
            + (f" {CALENDAR_STATE['location']}\n" if CALENDAR_STATE['location'] else "")
            + "\nReply YES to confirm or NO to cancel."
        )

    # ── TASKS (Google Tasks) ────────────────────────────────────────────
    from tools.google_tasks_intent import detect_tasks_intent
    
    tasks_intent = detect_tasks_intent(user_input)
    
    if tasks_intent:
        # ✅ RESEARCH: Stage 1 - Pattern matching handler
        trace["stage_reached"] = 1
        trace["stages_executed"].append(1)
        trace["confidence"] = tasks_intent.get("confidence", 0.85)
        
        intent_type = tasks_intent.get("type")
        logger.info(f"Tasks intent detected: {intent_type}", extra={"user_id": user_id})
        
        if intent_type == "list_tasks":
            result = list_tasks(show_completed=tasks_intent.get("show_completed", False))
            logger.debug(f"Tasks listed successfully", extra={"user_id": user_id})
            conversation_memory.add_turn(user_input, result)
            # ✅ RESEARCH: Log trace before returning
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result
        
        elif intent_type == "add_task":
            title = tasks_intent.get("title", "").strip()
            due = tasks_intent.get("due", "").strip()
            
            if not title:
                result = " Can't add task without a title. What task do you want to add?"
                logger.warning(f"Task add request without title", extra={"user_id": user_id})
            else:
                result = add_task(title, due=due if due else "")
                logger.info(f"Task added: {title}", extra={"user_id": user_id})
            
            conversation_memory.add_turn(user_input, result)
            # ✅ RESEARCH: Log trace before returning
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result
        
        elif intent_type == "complete_task":
            keyword = tasks_intent.get("keyword", "").strip()
            
            if not keyword:
                result = " Which task did you complete?"
                logger.warning(f"Task complete request without keyword", extra={"user_id": user_id})
            else:
                result = complete_task(keyword)
                logger.info(f"Task completed: {keyword}", extra={"user_id": user_id})
            
            conversation_memory.add_turn(user_input, result)
            # ✅ RESEARCH: Log trace before returning
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result
        
        elif intent_type == "delete_task":
            keyword = tasks_intent.get("keyword", "").strip()
            
            if not keyword:
                result = " Which task do you want to delete?"
                logger.warning(f"Task delete request without keyword", extra={"user_id": user_id})
            else:
                result = delete_task(keyword)
                logger.info(f"Task deleted: {keyword}", extra={"user_id": user_id})
            
            conversation_memory.add_turn(user_input, result)
            # ✅ RESEARCH: Log trace before returning
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result
        
        elif intent_type == "clear_completed":
            from tools.google_tasks_tool import clear_completed_tasks
            result = clear_completed_tasks()
            logger.info(f"Cleared completed tasks", extra={"user_id": user_id})
            conversation_memory.add_turn(user_input, result)
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result
        
        elif intent_type == "task_stats":
            from tools.google_tasks_tool import get_task_stats
            result = get_task_stats()
            logger.info(f"Retrieved task statistics", extra={"user_id": user_id})
            conversation_memory.add_turn(user_input, result)
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            return result

    # ── Web / Phone automation intent ──────────────────────────────────────
    web_intent = detect_web_intent(user_input)
    if web_intent:
        # 📱 Get web/phone context from conversation history
        web_context = get_feature_context("web")
        t = web_intent["type"]

        if t == "connect_phone_wifi":
            result = connect_phone_wifi(web_intent["ip"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "youtube_open":
            result = open_youtube()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "youtube_search":
            # Use recent searches from context if available
            query = web_intent.get("query") or (web_context.get("recent_searches", [""])[0] if web_context.get("recent_searches") else "")
            result = search_youtube(query)
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "spotify_open":
            result = open_spotify()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "spotify_search":
            # Use recent searches from context if available
            query = web_intent.get("query") or (web_context.get("recent_searches", [""])[0] if web_context.get("recent_searches") else "")
            result = spotify_search(query)
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "media_play_pause":
            result = play_pause_media()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "media_next":
            result = next_track()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "media_prev":
            result = previous_track()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "make_call":
            number = web_intent.get("number") or (web_context.get("recent_phone_numbers", [""])[0] if web_context.get("recent_phone_numbers") else "")
            result = make_call(number)
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "dial":
            number = web_intent.get("number") or (web_context.get("recent_phone_numbers", [""])[0] if web_context.get("recent_phone_numbers") else "")
            result = dial_number(number)
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "whatsapp_open":
            result = open_whatsapp()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "whatsapp_message":
            number = web_intent.get("number") or (web_context.get("recent_phone_numbers", [""])[0] if web_context.get("recent_phone_numbers") else "")
            result = whatsapp_message(number, web_intent.get("message", ""))
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "maps_open":
            result = open_maps()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "navigate":
            result = navigate_to(web_intent["destination"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "maps_search":
            result = search_maps(web_intent["query"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "set_alarm":
            result = set_alarm(web_intent["hour"], web_intent["minute"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "set_timer":
            result = set_timer(web_intent["seconds"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "mute":
            result = mute_phone()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "set_volume":
            result = set_volume_percent(web_intent["percent"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "volume_up":
            result = volume_up(web_intent.get("steps", 1))
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "volume_down":
            result = volume_down(web_intent.get("steps", 1))
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "set_brightness":
            result = set_brightness_percent(web_intent["percent"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "camera_open":
            result = open_camera()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "screenshot":
            result = take_screenshot()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "open_app":
            result = open_app(web_intent["app"])
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "bookmyshow_open":
            result = open_bookmyshow()
            conversation_memory.add_turn(user_input, result)
            return result
        if t == "book_movie":
            WEB_STATE.clear()
            WEB_STATE.update({
                "active": True,
                "type": "movie",
                "step": "city",
                "data": {"movie": web_intent["movie"]},
            })
            return f" Booking started for *{web_intent['movie']}*.\nWhich city?"

    # ── Active booking flow ────────────────────────────────────────────────
    if WEB_STATE.get("active"):
        step = WEB_STATE["step"]
        data = WEB_STATE["data"]

        if step == "city":
            data["city"] = user_input
            WEB_STATE["step"] = "date"
            return " Which date?"

        if step == "date":
            data["date"] = user_input
            WEB_STATE["step"] = "time"
            return " Preferred time?"

        if step == "time":
            data["time"] = user_input
            WEB_STATE["step"] = "confirm"
            return (
                f" Confirm booking:\n"
                f"Movie : {data.get('movie')}\n"
                f"City  : {data.get('city')}\n"
                f"Date  : {data.get('date')}\n"
                f"Time  : {data.get('time')}\n\n"
                "Reply YES or NO."
            )

        if step == "confirm":
            if user_lower == "yes":
                reset_web_state()
                result = start_booking(data["movie"], data["city"], data["date"], data["time"])
                conversation_memory.add_turn(user_input, result)
                return result
            reset_web_state()
            result = " Booking cancelled."
            conversation_memory.add_turn(user_input, result)
            return result

    # ── PDF RAG ────────────────────────────────────────────────────────────
    if use_pdf and pdf_store is not None:
        pdf_hits = pdf_store.smart_search(user_input, top_k=8)

        if pdf_hits:
            prompt = build_rag_prompt(user_input, pdf_hits, model_type)
            response = generate_llm(prompt, model_type)
            conversation_memory.add_turn(user_input, response)
            return response

        if pdf_store.text_chunks:
            fallback_chunks = pdf_store.text_chunks[:6]
            prompt = build_rag_prompt(user_input, fallback_chunks, model_type)
            response = generate_llm(prompt, model_type)
            conversation_memory.add_turn(user_input, response)
            return response

        result = " No content found in the PDF. Try rephrasing your question."
        conversation_memory.add_turn(user_input, result)
        return result

    # ── Fact / Wiki ────────────────────────────────────────────────────────
    if is_fact_question(user_input):
        fact = wiki_search(user_input)
        if fact:
            conversation_memory.add_turn(user_input, fact)
            return fact

    # ── Web search ─────────────────────────────────────────────────────────
    if use_web:
        # 📰 Get web/news context from conversation history
        web_context = get_feature_context("web")
        news_context = get_feature_context("news")
        
        # Use recent URLs or search queries from context if available
        search_query = user_input
        if web_context.get("recent_searches") and not any(kw in user_lower for kw in ["search", "find", "look"]):
            search_query = web_context["recent_searches"][0]
        
        news = news_search(search_query)
        web  = web_search(search_query)
        if news:
            context_blocks.append("NEWS:\n" + "\n".join(news))
        if web:
            context_blocks.append("WEB:\n" + "\n".join(web))

    # ── Stealth Mode: Apply Stylometric Defense (Experiment 5) ─────────────────
    # ✅ NEW: Linguistic masking to reduce user linkability across modes
    stealth_mode_active = False
    if user_id:
        user_prefs = UserPreferences.get_user_prefs(user_id)
        stealth_mode_active = user_prefs.get("stealth_mode", False)
    
    if stealth_mode_active:
        query_for_llm = StyleometricDefense.normalize_style(user_input)
        logger.debug(f"Stealth Mode activated: query style normalized", extra={
            "user_id": user_id,
            "original_length": len(user_input),
            "normalized_length": len(query_for_llm)
        })
    else:
        query_for_llm = user_input

    # ── Final LLM call with tone injection ─────────────────────────────────
    tone_instruction = tone_controller.get_tone_instruction()
    if tone_instruction:
        context_blocks.insert(0, f"TONE: {tone_instruction}")
    
    if use_web and context_blocks:
        news_items = [b.replace("NEWS:\n","") for b in context_blocks if b.startswith("NEWS:")]
        web_items  = [b.replace("WEB:\n","")  for b in context_blocks if b.startswith("WEB:")]
        prompt = build_web_prompt(query_for_llm, news_items, web_items, model_type)
    else:
        prompt = build_general_prompt(query_for_llm, context_blocks, model_type)

    # ✅ RESEARCH: Stage 4 - Fallback LLM reasoning with privacy boundary protection
    trace["stage_reached"] = 4
    trace["stages_executed"].append(4)
    trace["confidence"] = 0.3  # Low confidence fallback
    
    # ✅ NEW: Consent-based fallback for local LLM crashes (Experiment 4 privacy boundary)
    response = execute_llm_with_fallback(
        prompt=prompt,
        model_type=model_type,
        query=user_input,
        user_id=user_id,
        trace=trace
    )
    
    conversation_memory.add_turn(user_input, response)
    
    # ✅ RESEARCH: Log trace before final return
    trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
    log_orchestration_event(trace)
    
    return response

def _resolve_location_string(location_str: str, user_id: str = None) -> str:
    """
    Convert "my location", "current location", "here" to actual coordinates.
    """
    if location_str is None:
        return None
    
    location_str = location_str.strip().lower()
    
    # Check if it's a location placeholder
    if location_str in {"my location", "current location", "here", "my place"}:
        if user_id:
            user_location = get_user_location(user_id)
            if user_location:
                return f"{user_location['lat']},{user_location['lon']}"
        return None  # Return None if no saved location
    
    return location_str.strip()