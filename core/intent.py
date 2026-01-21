def detect_intent(text: str) -> str:
    t = text.lower()
    if "remember" in t:
        return "MEMORY"
    if "send email" in t or "mail" in t:
        return "EMAIL"
    return "CHAT"
