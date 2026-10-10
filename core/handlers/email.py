"""Gmail: read, search, and send/draft/reply/forward with explicit confirmation."""

import re

from core.handlers.base import Reply, Request
from core.model_manager import generate_llm
from tools.email_intent import EMAIL_REGEX, build_email_body, detect_email_intent, extract_email_fields
from tools.email_tool import (
    find_latest_message,
    format_inbox,
    forward_email,
    read_inbox,
    reply_to_email,
    save_draft,
    search_emails,
    send_email,
)

CONFIRM_WORDS = {"yes", "send", "confirm"}
CANCEL_WORDS = {"no", "cancel"}
REGEN_KEYWORDS = ("again please", "regenerate", "try again", "different", "again", "retry", "regen", "new")


def handle_pending(req: Request) -> Reply | None:
    """Runs first while an email is waiting for YES / NO / REGENERATE."""
    state = req.session.email
    if not state["pending"]:
        return None

    if req.lower in CONFIRM_WORDS:
        action = state["action"]
        if action == "draft":
            result = save_draft(state["to"], state["subject"], state["body"])
        elif action == "reply":
            result = reply_to_email(state["msg_id"], state["body"])
        elif action == "forward":
            result = forward_email(state["msg_id"], state["to"], state["body"])
        else:
            result = send_email(state["to"], state["subject"], state["body"])
        req.session.reset_email()
        return Reply(result)

    if req.lower in CANCEL_WORDS:
        req.session.reset_email()
        return Reply("Email cancelled.")

    keyword = next((k for k in REGEN_KEYWORDS if re.search(rf"\b{k}\b", req.lower)), None)
    if keyword:
        if not state["use_ai"]:
            return Reply("Regeneration only works with AI-written emails. Try: 'send email to <address> use ai <topic>'")
        feedback = req.text[req.lower.find(keyword) + len(keyword):].lstrip(" -:.,").strip()
        instruction = state["original_input"] or state["subject"] or "Professional email"
        if len(feedback) > 2:
            instruction += f"\nAdditional feedback: {feedback}"
        state["body"] = generate_llm(build_email_body(state["subject"], instruction, state["tone"]), req.model_type)
        note = f"\nFeedback applied: {feedback}" if len(feedback) > 2 else ""
        return Reply(
            f"New version:{note}\n\n{_preview(state)}\n\n"
            "Reply YES to send, NO to cancel, or REGENERATE <feedback> for another version."
        )

    return Reply(f"Pending confirmation:\n\n{_preview(state)}\n\nReply YES to confirm, NO to cancel, or REGENERATE for a new version.")


def handle(req: Request) -> Reply | None:
    intent = detect_email_intent(req.text)
    if intent is None:
        return None

    if intent == "read":
        return Reply(format_inbox(read_inbox(max_results=5, unread_only=True)))

    if re.search(r"\b(?:search|find|look for)\b", req.lower):
        m = re.search(r"(?:search|find|look for)\s+(?:emails?\s+(?:about|from|for)\s+)?(.+)", req.lower)
        return Reply(search_emails(m.group(1).strip() if m else req.text))

    fields = extract_email_fields(req.text)
    context = req.session.memory.get_feature_context("email")
    if context.get("email_tone") and fields.get("tone") == "professional":
        fields["tone"] = context["email_tone"]

    msg_id = ""
    if intent in {"reply", "forward"}:
        target, query = _find_target_message(req.text, intent, fields)
        if target is None:
            return Reply(f"I couldn't find an email matching '{query}'. Try 'reply to name@example.com saying …'.")
        msg_id = target["id"]
        if intent == "reply":
            fields["to"] = target["from"]
            fields["subject"] = target["subject"]
            fields["missing"] = [] if fields.get("body") else ["message content"]
        else:
            fields["missing"] = [] if fields.get("to") else ["recipient email address"]

    if not fields.get("to") and intent in {"send", "draft"} and context.get("recent_recipients"):
        fields["to"] = context["recent_recipients"][0]
        fields["missing"] = [m for m in fields["missing"] if m != "recipient email address"]

    if fields.get("missing"):
        return Reply("Please provide: " + ", ".join(fields["missing"]))

    body = fields.get("body") or ""
    use_ai = fields.get("use_ai", False)
    if intent != "forward" and (use_ai or (len(body.split()) < 8 and fields.get("subject"))):
        body = generate_llm(
            build_email_body(fields.get("subject") or "Email", body or fields.get("subject") or "Professional email", fields["tone"]),
            req.model_type,  # local mode never sends drafts to the cloud
        )
    elif not body and fields.get("subject"):
        body = fields["subject"]

    req.session.email.update(
        pending=True,
        action=intent,
        to=fields.get("to") or "",
        subject=fields.get("subject") or "",
        body=body,
        tone=fields.get("tone", "professional"),
        msg_id=msg_id,
        use_ai=use_ai,
        original_input=req.text,
    )
    hint = " REGENERATE or REGENERATE <feedback> for a new version." if use_ai else ""
    return Reply(f"Confirm {intent.upper()}:\n\n{_preview(req.session.email)}\n\nReply YES to send or NO to cancel.{hint}")


def _find_target_message(text: str, intent: str, fields: dict) -> tuple[dict | None, str]:
    """Pick the inbox message a reply/forward refers to."""
    m = re.search(r"\bfrom\s+(" + EMAIL_REGEX + r"|\w+)", text, re.IGNORECASE)
    if m:
        query = f"from:{m.group(1)}"
    elif intent == "reply" and fields.get("to"):
        query = f"from:{fields['to']}"
    else:
        about = re.search(r"\babout\s+(.+?)(?:\s+to\s+\S+@\S+|$)", text, re.IGNORECASE)
        query = about.group(1) if about else "in:inbox"

    if intent == "forward":
        # Recipient is the address after "to", not the sender we searched for.
        to = re.search(r"\bto\s+(" + EMAIL_REGEX + ")", text, re.IGNORECASE)
        fields["to"] = to.group(1) if to else None
    return find_latest_message(query), query


def _preview(state: dict) -> str:
    return (
        f"Action : {state['action'].upper()}\n"
        f"To     : {state['to']}\n"
        f"Subject: {state['subject'] or '(no subject)'}\n\n"
        f"{state['body']}"
    )
