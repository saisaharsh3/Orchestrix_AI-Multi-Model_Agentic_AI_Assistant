"""
google_tasks_tool.py - Google Tasks integration
Uses same OAuth credentials as Gmail/Calendar.
Enable "Tasks API" in Google Cloud Console.
"""

import os
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_PATH = "credentials/credentials.json"
TOKEN_PATH       = "credentials/token.json"


def _get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs("credentials", exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("tasks", "v1", credentials=creds)


def _get_default_tasklist(service) -> str:
    lists = service.tasklists().list().execute()
    items = lists.get("items", [])
    return items[0]["id"] if items else "@default"




def add_task(title: str, notes: str = "", due: str = "") -> str:
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)
        task     = {"title": title}

        if notes:
            task["notes"] = notes

        if due:
            try:
                dt = datetime.strptime(due, "%Y-%m-%d")
                task["due"] = dt.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass

        service.tasks().insert(tasklist=list_id, body=task).execute()
        return f"Task added: {title}" + (f" (due {due})" if due else "")

    except HttpError as e:
        return f"Error adding task: {e}"
    except Exception as e:
        return f"Error: {e}"




def list_tasks(show_completed: bool = False) -> str:
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(
            tasklist=list_id,
            showCompleted=show_completed,
            showHidden=False,
            maxResults=20,
        ).execute()

        tasks = result.get("items", [])

        if not tasks:
            return "No tasks found. Add one by saying 'add task buy milk'."

        lines = [f"Tasks ({len(tasks)}):"]
        for t in tasks:
            status = "done" if t.get("status") == "completed" else "pending"
            due    = ""
            if t.get("due"):
                try:
                    dt  = datetime.fromisoformat(t["due"].replace("Z", "+00:00"))
                    due = f" - due {dt.strftime('%b %d')}"
                except Exception:
                    pass
            lines.append(f"- [{status}] {t['title']}{due}")

        return "\n".join(lines)

    except HttpError as e:
        return f"Error listing tasks: {e}"
    except Exception as e:
        return f"Error: {e}"




def complete_task(title_keyword: str) -> str:
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(
            tasklist=list_id, showCompleted=False
        ).execute()
        tasks = result.get("items", [])

        matched = [t for t in tasks if title_keyword.lower() in t["title"].lower()]
        if not matched:
            return f"No task found matching '{title_keyword}'."

        task          = matched[0]
        task["status"] = "completed"
        service.tasks().update(
            tasklist=list_id, task=task["id"], body=task
        ).execute()
        return f"Task completed: {task['title']}"

    except HttpError as e:
        return f"Error completing task: {e}"
    except Exception as e:
        return f"Error: {e}"




def delete_task(title_keyword: str) -> str:
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(tasklist=list_id).execute()
        tasks  = result.get("items", [])

        matched = [t for t in tasks if title_keyword.lower() in t["title"].lower()]
        if not matched:
            return f"No task found matching '{title_keyword}'."

        task = matched[0]
        service.tasks().delete(tasklist=list_id, task=task["id"]).execute()
        return f"Task deleted: {task['title']}"

    except HttpError as e:
        return f"Error deleting task: {e}"
    except Exception as e:
        return f"Error: {e}"