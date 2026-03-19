"""
tone_controller.py - Manage response tone
"""

TONE_PROMPTS = {
    "funny": "Respond with humor and wit. Make it entertaining while being accurate.",
    "formal": "Respond professionally and formally. Use proper language and structure.",
    "brief": "Keep the response SHORT and to the point. Max 2-3 sentences.",
    "detailed": "Provide a comprehensive, detailed response with examples.",
    "simple": "Explain in simple terms that anyone can understand. Avoid jargon.",
}

class ToneController:
    def __init__(self):
        self.current_tone = "formal"
    
    def set_tone(self, tone: str) -> str:
        """Set the response tone."""
        if tone in TONE_PROMPTS:
            self.current_tone = tone
            return f" Tone set to: {tone.upper()}"
        return f" Unknown tone. Available: {', '.join(TONE_PROMPTS.keys())}"
    
    def get_tone_instruction(self) -> str:
        """Get the instruction to inject into prompts."""
        return TONE_PROMPTS.get(self.current_tone, "")
    
    def get_current_tone(self) -> str:
        return self.current_tone

# Global instance
tone_controller = ToneController()