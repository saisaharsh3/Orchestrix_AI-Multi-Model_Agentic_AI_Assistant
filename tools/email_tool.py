"""
email_tool.py — Full Gmail automation
──────────────────────────────────────
Supports: send, draft, read inbox, reply, forward
Uses Gmail API with OAuth2 (credentials/credentials.json)
"""

import base64
from email.message import EmailMessage

from googleapiclient.errors import HttpError

from tools.google_auth import get_service


def _get_gmail_service():
    return get_service("gmail", "v1")


def _encode_message(msg: EmailMessage) -> dict:
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


def send_email(to: str, subject: str, body: str) -> str:
    try:
        service = _get_gmail_service()
        msg = EmailMessage()
        msg["To"]      = to
        msg["From"]    = "me"
        msg["Subject"] = subject or "(no subject)"
        msg.set_content(body)

        service.users().messages().send(
            userId="me", body=_encode_message(msg)
        ).execute()
        return f" Email sent to {to}."
    except HttpError as e:
        return f" Gmail error: {e}"
    except Exception as e:
        return f" Error sending email: {e}"


def save_draft(to: str, subject: str, body: str) -> str:
    try:
        service = _get_gmail_service()
        msg = EmailMessage()
        msg["To"]      = to
        msg["From"]    = "me"
        msg["Subject"] = subject or "(no subject)"
        msg.set_content(body)

        service.users().drafts().create(
            userId="me",
            body={"message": _encode_message(msg)},
        ).execute()
        return f" Draft saved (To: {to}, Subject: {subject})."
    except HttpError as e:
        return f" Gmail error: {e}"
    except Exception as e:
        return f" Error saving draft: {e}"


def read_inbox(max_results: int = 5, unread_only: bool = True) -> list[dict]:
    """
    Returns list of email dicts: {id, from, subject, snippet, date}
    """
    try:
        service = _get_gmail_service()
        query   = "is:unread" if unread_only else ""

        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            q=query,
            labelIds=["INBOX"],
        ).execute()

        messages = results.get("messages", [])
        emails   = []

        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            emails.append({
                "id":      m["id"],
                "from":    headers.get("From", "Unknown"),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": msg.get("snippet", ""),
                "date":    headers.get("Date", ""),
            })

        return emails

    except HttpError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": str(e)}]


def format_inbox(emails: list[dict]) -> str:
    if not emails:
        return " No unread emails."
    if "error" in emails[0]:
        return f" {emails[0]['error']}"

    lines = [f" *{len(emails)} unread email(s):*\n"]
    for i, e in enumerate(emails, 1):
        lines.append(
            f"*{i}.* From: {e['from']}\n"
            f"   Subject: {e['subject']}\n"
            f"   {e['snippet'][:100]}...\n"
        )
    return "\n".join(lines)


def get_email_body(message_id: str) -> str:
    try:
        service = _get_gmail_service()
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        parts = msg.get("payload", {}).get("parts", [])
        body  = ""

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    break

        if not body:

            data = msg.get("payload", {}).get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        return body.strip() or "(empty body)"

    except Exception as e:
        return f" Could not read email: {e}"


def reply_to_email(message_id: str, body: str) -> str:
    try:
        service = _get_gmail_service()


        orig = service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID", "To"],
        ).execute()

        headers     = {h["name"]: h["value"] for h in orig["payload"]["headers"]}
        thread_id   = orig.get("threadId", "")
        reply_to    = headers.get("From", "")
        orig_subject = headers.get("Subject", "")
        msg_id      = headers.get("Message-ID", "")

        subject = orig_subject if orig_subject.startswith("Re:") else f"Re: {orig_subject}"

        msg = EmailMessage()
        msg["To"]         = reply_to
        msg["From"]       = "me"
        msg["Subject"]    = subject
        msg["In-Reply-To"] = msg_id
        msg["References"] = msg_id
        msg.set_content(body)

        encoded = _encode_message(msg)
        encoded["threadId"] = thread_id

        service.users().messages().send(userId="me", body=encoded).execute()
        return f" Reply sent to {reply_to}."

    except HttpError as e:
        return f" Gmail error: {e}"
    except Exception as e:
        return f" Reply failed: {e}"


def forward_email(message_id: str, to: str, note: str = "") -> str:
    try:
        service  = _get_gmail_service()
        orig_body = get_email_body(message_id)

        orig = service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()

        headers      = {h["name"]: h["value"] for h in orig["payload"]["headers"]}
        orig_from    = headers.get("From", "")
        orig_subject = headers.get("Subject", "")
        orig_date    = headers.get("Date", "")

        fwd_body = (
            f"{note}\n\n" if note else ""
        ) + (
            f"---------- Forwarded message ----------\n"
            f"From: {orig_from}\n"
            f"Date: {orig_date}\n"
            f"Subject: {orig_subject}\n\n"
            f"{orig_body}"
        )

        subject = f"Fwd: {orig_subject}" if not orig_subject.startswith("Fwd:") else orig_subject

        msg = EmailMessage()
        msg["To"]      = to
        msg["From"]    = "me"
        msg["Subject"] = subject
        msg.set_content(fwd_body)

        service.users().messages().send(
            userId="me", body=_encode_message(msg)
        ).execute()
        return f" Email forwarded to {to}."

    except HttpError as e:
        return f" Gmail error: {e}"
    except Exception as e:
        return f" Forward failed: {e}"


def find_latest_message(query: str) -> dict | None:
    """Most recent message matching a Gmail search query, as {id, from, subject}."""
    service = _get_gmail_service()
    found = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
    messages = found.get("messages", [])
    if not messages:
        return None
    msg = service.users().messages().get(
        userId="me", id=messages[0]["id"], format="metadata",
        metadataHeaders=["From", "Subject"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": messages[0]["id"],
        "from": headers.get("From", "Unknown"),
        "subject": headers.get("Subject", "(no subject)"),
    }


def search_emails(query: str, max_results: int = 5) -> str:
    try:
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return f" No emails found for: *{query}*"

        emails = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            emails.append(
                f"• From: {headers.get('From','?')}\n"
                f"  Subject: {headers.get('Subject','?')}\n"
                f"  Date: {headers.get('Date','?')}"
            )

        return f" Found {len(emails)} email(s) for *{query}*:\n\n" + "\n\n".join(emails)

    except Exception as e:
        return f" Search failed: {e}"
