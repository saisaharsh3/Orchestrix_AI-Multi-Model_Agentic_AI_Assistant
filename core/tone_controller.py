"""
tone_controller.py - Response tone presets.

The active tone is stored per user on their Session (core/session.py).
"""

TONE_PROMPTS = {
    "funny": "Respond with humor and wit. Make it entertaining while being accurate.",
    "formal": "Respond professionally and formally. Use proper language and structure.",
    "brief": "Keep the response SHORT and to the point. Max 2-3 sentences.",
    "detailed": "Provide a comprehensive, detailed response with examples.",
    "simple": "Explain in simple terms that anyone can understand. Avoid jargon.",
}


def is_valid_tone(tone: str) -> bool:
    return tone in TONE_PROMPTS


def tone_instruction(tone: str) -> str:
    """Instruction to inject into prompts for the given tone ('' if unknown)."""
    return TONE_PROMPTS.get(tone, "")
