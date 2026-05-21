"""
email_intent.py — Smart email intent detection & field extraction
─────────────────────────────────────────────────────────────────
Detects: send, reply, forward, read inbox, draft
Extracts: to, subject, body, tone, thread_id (for reply/forward)
"""

import re

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"



SEND_TRIGGERS = [
    "send an email", "send email", "mail to", "email to",
    "compose an email", "send a mail", "write an email",
    "write a mail", "compose mail", "shoot an email",
]

REPLY_TRIGGERS = [
    "reply to", "respond to", "reply back", "write back to",
    "answer the email", "respond to the email",
]

FORWARD_TRIGGERS = [
    "forward", "forward this email", "forward the email",
]

READ_TRIGGERS = [
    "check my email", "check inbox", "read my emails",
    "show my emails", "any new emails", "what emails",
    "unread emails", "show inbox", "check mail",
]

DRAFT_TRIGGERS = [
    "draft an email", "save as draft", "create a draft",
    "draft email", "save draft",
]

AI_GENERATION_TRIGGERS = [
    "use ai", "use ai to write", "ai write", "ai generate",
    "let ai write", "have ai write", "let ai compose",
    "have ai compose", "ai compose", "ai write about",
]


def detect_email_intent(text: str) -> str | None:
    """
    Returns intent type: 'send' | 'reply' | 'forward' | 'read' | 'draft' | None
    """
    t = text.lower()

    if any(trigger in t for trigger in READ_TRIGGERS):
        return "read"
    if any(trigger in t for trigger in REPLY_TRIGGERS):
        return "reply"
    if any(trigger in t for trigger in FORWARD_TRIGGERS):
        return "forward"
    if any(trigger in t for trigger in DRAFT_TRIGGERS):
        return "draft"
    if any(trigger in t for trigger in SEND_TRIGGERS):
        return "send"

    
    if re.search(r"email\s+\w+\s+about", t):
        return "send"

    return None


def should_use_ai_generation(text: str) -> bool:
    """
    Check if user wants AI to generate email content.
    Keywords: 'use ai', 'ai write', 'ai generate', etc.
    """
    t = text.lower()
    return any(trigger in t for trigger in AI_GENERATION_TRIGGERS)


def extract_email_fields(text: str) -> dict:
    """
    Smartly extract to, subject, body, tone from natural language.
    Returns dict with 'missing' list if required fields absent.
    Detects 'use ai' keyword to trigger AI-based email generation.
    """
    # Check if AI generation requested before processing
    use_ai = should_use_ai_generation(text)
    
    # Remove AI keywords from text to avoid interfering with extraction
    clean_text = text
    for trigger in AI_GENERATION_TRIGGERS:
        clean_text = clean_text.lower().replace(trigger, " ")
    
    result = {
        "to": None,
        "subject": None,
        "body": None,
        "tone": "professional",   
        "use_ai": use_ai,
        "missing": [],
    }

    
    match = re.search(EMAIL_REGEX, clean_text)
    if match:
        result["to"] = match.group()

    
    if not result["to"]:
        name_match = re.search(
            r"(?:email|mail|send\s+(?:an?\s+)?(?:email|mail))\s+(?:to\s+)?([A-Z][a-z]+)",
            clean_text,
        )
        if name_match:
            result["to"] = name_match.group(1)  

    
    patterns_subject = [
        r"(?:subject[:\s]+)(.+?)(?:\s+(?:saying|body|message|and\s+say)|$)",
        r"(?:about\s+)(.+?)(?:\s+(?:saying|body|message|telling|and\s+say)|$)",
        r"(?:regarding\s+)(.+?)(?:\s+(?:saying|body|message)|$)",
        r"(?:topic[:\s]+)(.+?)(?:\s+(?:saying|body|message)|$)",
    ]
    for pattern in patterns_subject:
        m = re.search(pattern, clean_text, re.IGNORECASE)
        if m:
            result["subject"] = m.group(1).strip().title()
            break

    
    patterns_body = [
        r"(?:saying|say|message|body|that\s+says?)[:\s]+(.+?)(?:\s+(?:subject|about|to\s+\S+@)|$)",
        r"(?:tell\s+(?:him|her|them)\s+)(.+?)$",
        r"(?:content[:\s]+)(.+?)$",
    ]
    for pattern in patterns_body:
        m = re.search(pattern, clean_text, re.IGNORECASE)
        if m:
            result["body"] = m.group(1).strip()
            break

    
    t = clean_text.lower()
    if any(w in t for w in ["formal", "professional", "official"]):
        result["tone"] = "formal"
    elif any(w in t for w in ["friendly", "casual", "informal", "warm"]):
        result["tone"] = "casual"
    elif any(w in t for w in ["urgent", "asap", "immediately", "critical"]):
        result["tone"] = "urgent"
    elif any(w in t for w in ["polite", "kind", "gentle"]):
        result["tone"] = "polite"

    
    if not result["to"] or "@" not in str(result["to"]):
        result["missing"].append("recipient email address")
    if not result["body"] and not result["subject"]:
        result["missing"].append("message content")

    return result




def build_email_body(subject: str, raw_content: str, tone: str) -> str:
    """
    Expand a short instruction into a full email body.
    Called before confirmation if body is very short (<20 words).
    """
    tone_instructions = {
        "formal":       "Write in a formal, professional tone.",
        "casual":       "Write in a friendly, casual tone.",
        "urgent":       "Write with urgency, keep it brief and direct.",
        "polite":       "Write in a polite and respectful tone.",
        "professional": "Write in a clear, professional tone.",
    }
    instruction = tone_instructions.get(tone, tone_instructions["professional"])

    return f"""
Subject hint: {subject or 'N/A'}
User instruction: {raw_content}
Tone: {instruction}

Write a complete, ready-to-send email body. No subject line, no placeholders. 
Just the body text starting with a greeting and ending with a sign-off.
""".strip()