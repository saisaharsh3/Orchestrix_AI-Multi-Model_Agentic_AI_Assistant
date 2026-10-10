"""
feature_intent.py - Master NLP Intent Detector with Confidence & Ambiguity Detection
"""

import re

from tools.google_tasks_intent import detect_tasks_intent

# Confidence thresholds
CONFIDENCE_HIGH = 0.9  # Very sure of intent
CONFIDENCE_MEDIUM = 0.6  # Fairly sure, might be ambiguous
CONFIDENCE_LOW = 0.3  # Very ambiguous, ask user or provide both


def detect_feature_intent(user_input: str) -> dict | None:
    """
    Master intent detection with confidence scoring.
    Returns: intent dict WITH confidence level
    Format: {"type": "...", "confidence": 0.0-1.0, "alternatives": [...]}
    """

    lower = user_input.lower()

    # ──────────────────────────────────────────────────────────────────────
    # QUICK HARDCODED CHECKS
    # ──────────────────────────────────────────────────────────────────────

    tone_match = _detect_tone_simple(lower)
    if tone_match:
        tone_match["confidence"] = CONFIDENCE_HIGH
        tone_match["alternatives"] = []
        return tone_match

    history_match = _detect_history_simple(lower)
    if history_match:
        history_match["confidence"] = CONFIDENCE_HIGH
        history_match["alternatives"] = []
        return history_match

    # ────────────────────────────────────────────────────────────────────
    # DETECT TASKS INTENT (High priority - accurate pattern matching)
    # ────────────────────────────────────────────────────────────────────

    tasks_match = detect_tasks_intent(user_input)
    if tasks_match:
        tasks_match["confidence"] = CONFIDENCE_HIGH
        tasks_match["alternatives"] = []
        return tasks_match

    # ──────────────────────────────────────────────────────────────────────
    # DETECT AMBIGUITY: Does this request have multiple valid interpretations?
    # ──────────────────────────────────────────────────────────────────────

    nlp_keywords = [
        "send", "email", "message", "draft", "reply", "forward",
        "add event", "schedule", "meeting", "calendar", "tomorrow", "next week",
        "call", "dial", "whatsapp", "text", "sms",
        "play", "music", "spotify", "youtube", "search",
        "map", "direction", "route", "nearby", "set maps", "put maps",
        "book", "booking", "movie", "theater",
        "set alarm", "timer", "alarm",
        "open", "app", "application",
        "navigate", "travel", "get directions", "how to go", "how do i go"
    ]

    has_nlp_keyword = any(keyword in lower for keyword in nlp_keywords)

    if has_nlp_keyword:
        # Skip expensive LLM intent detection when API quota is limited
        # Just use pattern matching instead - sufficient for most use cases
        pattern_result = _detect_intent_by_patterns(user_input)
        if pattern_result:
            pattern_result["confidence"] = CONFIDENCE_MEDIUM
            pattern_result = _add_alternatives(user_input, pattern_result)
            return pattern_result

    return None


def _add_alternatives(user_input: str, detected_intent: dict) -> dict:
    """
    Detect if user's request could have MULTIPLE valid responses.
    E.g., "how do i go to airport" → could want BOTH maps AND info
    """

    lower = user_input.lower()
    alternatives = []

    # ──── MAPS + INFO AMBIGUITY ────────────────────────────────────────
    # "How do I go to X", "directions to X", "how to reach X"
    # Could want: Maps directions OR General information
    if any(phrase in lower for phrase in ["how do i go", "how to get to", "directions to", "how to reach", "way to"]):
        if detected_intent.get("type") == "maps_directions":
            # They got maps - but also offer general info
            alternatives.append({
                "type": "info_response",
                "trigger": "Also provide general transportation info?",
                "priority": "secondary"
            })
            detected_intent["confidence"] = CONFIDENCE_MEDIUM  # Lower confidence - ambiguous

    # ──── EMAIL AMBIGUITY ────────────────────────────────────────────────
    # "Message X" → could be WhatsApp, email, or SMS
    if any(word in lower for word in ["message", "contact", "reach out", "send to"]):
        if detected_intent.get("type") == "email_detected":
            alternatives.append({
                "type": "phone_detected",
                "intent": "whatsapp",
                "trigger": "Send via WhatsApp instead?",
                "priority": "secondary"
            })

    # ──── CALENDAR + REMINDER AMBIGUITY ────────────────────────────────
    # "Remind me", "schedule", "add event"
    if any(word in lower for word in ["remind", "schedule", "set alarm"]):
        if detected_intent.get("type") == "calendar_detected":
            alternatives.append({
                "type": "phone_detected",
                "intent": "set_alarm",
                "trigger": "Set as alarm instead?",
                "priority": "secondary"
            })

    detected_intent["alternatives"] = alternatives

    # If alternatives exist and confidence is medium, lower it more
    if alternatives and detected_intent.get("confidence", 0) >= CONFIDENCE_MEDIUM:
        detected_intent["confidence"] = CONFIDENCE_MEDIUM

    return detected_intent


def _detect_tone_simple(lower: str) -> dict | None:
    """Detect explicit tone-setting requests (not just mentions of tone words)."""

    # ONLY match explicit tone commands like "be funny", "set tone to formal", etc.
    # NOT generic questions that happen to contain these words

    tone_patterns = {
        r"(be|answer|respond|talk|write|sound|speak)\s+(funny|comic|humorous|jokes)": "funny",
        r"(be|answer|respond|talk|write)\s+(formal|professional|business)": "formal",
        r"(be|answer|respond|talk|write)\s+(brief|short|concise)": "brief",
        r"answer\s+(in\s+)?(detail|detailed|elaborate)": "detailed",
        r"(explain|teach)\s+(like i'm|like i am|like i'm a|like a child|simple|simply|easy)": "simple",
        r"(set\s+)?tone\s+(to\s+)?(funny|formal|brief|detailed|simple)": "detected",
    }

    for pattern, tone_name in tone_patterns.items():
        match = re.search(pattern, lower)
        if match:
            # Extract tone from pattern if not explicit
            if tone_name == "detected":
                match.groups()
                tone_text = match.group(0).lower()
                if "funny" in tone_text:
                    tone_name = "funny"
                elif "formal" in tone_text:
                    tone_name = "formal"
                elif "brief" in tone_text:
                    tone_name = "brief"
                elif "detailed" in tone_text:
                    tone_name = "detailed"
                elif "simple" in tone_text:
                    tone_name = "simple"
            return {"type": "set_tone", "tone": tone_name}

    return None


def _detect_history_simple(lower: str) -> dict | None:
    """Detect history requests."""
    if any(word in lower for word in ["search history", "find conversation", "search chat"]):
        match = re.search(r"(?:search|find)\s+(?:conversation|chat|message|history)?\s*(?:about|for)?\s+(.+)", lower)
        if match:
            return {"type": "search_history", "query": match.group(1).strip()}

    if any(word in lower for word in ["show history", "list history", "all conversations"]):
        return {"type": "list_history"}

    return None


def _detect_intent_by_patterns(user_input: str) -> dict | None:
    """Fallback pattern matching."""
    lower = user_input.lower()

    # Maps patterns
    if any(word in lower for word in ["direction", "route", "how to get", "how do i go"]):
        match = re.search(r"(?:to|towards?)\s+([^?]+?)(?:\s*\?|$)", lower)
        dest = match.group(1).strip() if match else ""
        return {
            "type": "maps_directions",
            "confidence": CONFIDENCE_MEDIUM,
            "origin": "my location",
            "destination": dest
        }

    if any(word in lower for word in ["nearby", "near me"]):
        match = re.search(r"(?:find|near)\s+(\w+)", lower)
        place = match.group(1) if match else "restaurants"
        return {
            "type": "maps_nearby",
            "confidence": CONFIDENCE_MEDIUM,
            "place_type": place,
            "location": "my location"
        }

    # Email patterns
    if any(word in lower for word in ["send email", "email", "compose"]):
        return {
            "type": "email_detected",
            "confidence": CONFIDENCE_MEDIUM,
            "intent": "send"
        }

    return None
