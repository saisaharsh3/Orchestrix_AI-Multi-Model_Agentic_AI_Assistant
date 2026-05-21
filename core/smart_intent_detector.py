"""
smart_intent_detector.py - AI-powered intent detection without hardcoded keywords
Uses LLM to intelligently understand user intent and asks for clarification when unsure.
"""

import json
import re
from core.model_manager import generate_llm


def detect_intent_with_llm(user_input: str) -> dict | None:
    """
    Use LLM to intelligently detect intent without hardcoded keywords.
    Returns intent with confidence score.
    """
    
    prompt = f"""Analyze this user message and determine what action they want. Be intelligent about context.

User message: "{user_input}"

Respond ONLY with valid JSON (no markdown, no backticks, just raw JSON):
{{
    "intent": "maps|email|calendar|task|search|general|unclear",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of why you chose this intent",
    "suggested_action": "what the bot should do",
    "clarification_needed": true/false,
    "clarifying_questions": ["question1 if any", "question2 if any"]
}}

Intent guidelines:
- "maps": includes directions, navigation, routes, location queries, nearby places, distance, landmarks
- "email": compose, send, read, reply, forward emails, check inbox
- "calendar": add events, schedule meetings, check calendar, reminders
- "task": add todo, task management, checklist
- "search": looking for information across tools
- "general": general conversation, questions, answers
- "unclear": could be 2+ different things

Examples:
- "directions from Delhi to Jaipur" → maps (even without "maps" keyword)
- "how do I get to the airport" → maps
- "what's in Delhi" → unclear (could be maps place info OR general trivia)
- "send message to john" → email
- "coffee shops near me" → maps
- "where are my meeting notes" → search"""

    try:
        response = generate_llm(prompt, "api")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            # Clean up any escaped newlines
            json_str = json_str.replace('\\n', ' ')
            result = json.loads(json_str)
            return result
    except Exception as e:
        print(f"[DEBUG] Intent detection error: {e}")
        return None
    
    return None


def should_ask_for_clarification(intent_result: dict) -> bool:
    """Check if we should ask the user for clarification."""
    if not intent_result:
        return False
    
    confidence = intent_result.get("confidence", 0)
    needs_clarification = intent_result.get("clarification_needed", False)
    intent = intent_result.get("intent", "general")
    
    # Ask if confidence is too low or explicitly needed
    return needs_clarification or (confidence < 0.6 and intent != "general")


def get_clarification_prompt(intent_result: dict) -> str:
    """Generate user-friendly clarification message."""
    questions = intent_result.get("clarifying_questions", [])
    reasoning = intent_result.get("reasoning", "")
    
    if not questions:
        return f"I'm not quite sure what you mean. Could you clarify? ({reasoning})"
    
    msg = f"I detected this could mean a few things:\n\n"
    for i, q in enumerate(questions, 1):
        msg += f"{i}. {q}\n"
    
    msg += "\nWhich one did you mean?"
    return msg


def extract_maps_details(user_input: str, intent_result: dict) -> dict | None:
    """Extract origin and destination for maps from user input."""
    t = user_input.lower()
    reasoning = intent_result.get("reasoning", "").lower()
    
    # Check if it's a directions query
    if "direction" in reasoning or "route" in reasoning or "get from" in reasoning or "get to" in reasoning:
        # Try to extract locations
        from_patterns = [r"from\s+(.+?)\s+to", r"from\s+(.+?)(?:\s+to|\s+$)"]
        to_patterns = [r"to\s+(.+?)(?:\s+via|\s+$)", r"to\s+(.+)$"]
        
        origin = None
        destination = None
        
        for pattern in from_patterns:
            m = re.search(pattern, t)
            if m:
                origin = m.group(1).strip()
                break
        
        for pattern in to_patterns:
            m = re.search(pattern, t)
            if m:
                destination = m.group(1).strip()
                break
        
        if origin and destination:
            return {
                "type": "maps_directions",
                "origin": origin,
                "destination": destination,
                "confidence": intent_result.get("confidence", 0)
            }
    
    # Check if it's a nearby/place search
    if "nearby" in reasoning or "near" in reasoning or "around" in reasoning:
        m = re.search(r"(?:find|search|near|nearby)\s+(.+?)(?:\s+near|\s+in|$)", t)
        if m:
            place_type = m.group(1).strip()
            return {
                "type": "maps_nearby",
                "place_type": place_type,
                "location": "current location",
                "confidence": intent_result.get("confidence", 0)
            }
    
    # Generic maps search
    m = re.search(r"(?:search|find)\s+(?:for\s+)?(.+?)(?:\s+in|$)", t)
    if m:
        return {
            "type": "maps_search",
            "query": m.group(1).strip(),
            "confidence": intent_result.get("confidence", 0)
        }
    
    return None


def extract_email_details(user_input: str, intent_result: dict) -> dict | None:
    """Extract email action from intent."""
    t = user_input.lower()
    reasoning = intent_result.get("reasoning", "").lower()
    
    if "send" in reasoning or "compose" in reasoning:
        return {"type": "email_send", "confidence": intent_result.get("confidence", 0)}
    
    if "read" in reasoning or "inbox" in reasoning:
        return {"type": "email_read", "confidence": intent_result.get("confidence", 0)}
    
    if "search" in reasoning or "find" in reasoning:
        return {"type": "email_search", "confidence": intent_result.get("confidence", 0)}
    
    if "reply" in reasoning or "respond" in reasoning:
        return {"type": "email_reply", "confidence": intent_result.get("confidence", 0)}
    
    return None