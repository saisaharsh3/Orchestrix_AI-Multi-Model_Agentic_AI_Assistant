import re

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def detect_email_intent(text: str) -> bool:
    """
    Detect if user wants to send an email
    """
    t = text.lower()
    triggers = [
        "send an email",
        "send email",
        "mail to",
        "email to",
        "compose an email",
        "send a mail",
    ]
    return any(trigger in t for trigger in triggers)


def extract_email_fields(text: str) -> dict:
    """
    Extract recipient, subject, and body from natural language
    """
    recipient = None
    subject = None
    body = None

    # Extract email address
    match = re.search(EMAIL_REGEX, text)
    if match:
        recipient = match.group()

    # Subject
    if "about" in text.lower():
        subject = text.lower().split("about", 1)[1].split("saying")[0].strip().title()

    # Body
    if "saying" in text.lower():
        body = text.lower().split("saying", 1)[1].strip()

    return {
        "to": recipient,
        "subject": subject,
        "body": body,
    }
