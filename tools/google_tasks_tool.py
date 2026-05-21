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
    """Add a new task with optional due date."""
    try:
        if not title or len(title.strip()) < 2:
            return "❌ Task title must be at least 2 characters."
        
        service  = _get_service()
        list_id  = _get_default_tasklist(service)
        task     = {"title": title.strip()}

        if notes:
            task["notes"] = notes.strip()

        if due:
            try:
                dt = datetime.strptime(due, "%Y-%m-%d")
                task["due"] = dt.replace(tzinfo=timezone.utc).isoformat()
                due_display = f" (due {dt.strftime('%b %d')})"
            except ValueError:
                due_display = ""
        else:
            due_display = ""

        service.tasks().insert(tasklist=list_id, body=task).execute()
        return f"✅ Task added: {title}{due_display}"

    except HttpError as e:
        return f"❌ Error adding task: {e}"
    except Exception as e:
        return f"❌ Error: {e}"




def list_tasks(show_completed: bool = False, search: str = "", status_filter: str = "") -> str:
    """List tasks with deduplication, filtering, and better formatting."""
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(
            tasklist=list_id,
            showCompleted=True,  # Get all, then filter locally
            showHidden=False,
            maxResults=50,
        ).execute()

        all_tasks = result.get("items", [])

        if not all_tasks:
            return "📋 No tasks found. Add one by saying 'add task buy milk'."

        # Deduplicate by id
        seen = set()
        unique_tasks = []
        for t in all_tasks:
            task_id = t.get("id")
            if task_id not in seen:
                seen.add(task_id)
                unique_tasks.append(t)

        # Filter tasks
        filtered = []
        for t in unique_tasks:
            is_completed = t.get("status") == "completed"
            
            if is_completed and not show_completed:
                continue
            
            if status_filter == "pending" and is_completed:
                continue
            if status_filter == "completed" and not is_completed:
                continue
            
            if search and search.lower() not in t["title"].lower():
                continue
            
            filtered.append(t)

        if not filtered:
            return "✅ No matching tasks found."

        # Group by status
        pending = [t for t in filtered if t.get("status") != "completed"]
        completed = [t for t in filtered if t.get("status") == "completed"]
        
        lines = []
        lines.append(f"📋 TASKS ({len(pending)} pending, {len(completed)} done)")
        lines.append("")
        
        if pending:
            lines.append("🔵 PENDING:")
            for i, t in enumerate(pending, 1):
                title = t.get("title", "").strip()
                if not title:
                    continue  # Skip empty titles
                due_str = ""
                if t.get("due"):
                    try:
                        dt = datetime.fromisoformat(t["due"].replace("Z", "+00:00"))
                        due_str = f" 📅 {dt.strftime('%b %d')}"
                    except Exception:
                        pass
                lines.append(f"  {i}. {title}{due_str}")
        
        if show_completed and completed:
            lines.append("")
            lines.append("✅ COMPLETED:")
            for t in completed:
                title = t.get("title", "").strip()
                if not title:
                    continue  # Skip empty titles
                lines.append(f"  ✓ {title}")

        return "\n".join(lines)

    except HttpError as e:
        return f"❌ Error listing tasks: {e}"
    except Exception as e:
        return f"❌ Error: {e}"




def complete_task(title_keyword: str) -> str:
    """Mark a task as complete by keyword matching."""
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(
            tasklist=list_id, showCompleted=False
        ).execute()
        tasks = result.get("items", [])
        
        if not tasks:
            return f"❌ No pending tasks found. All tasks are completed!"

        # Try exact match first, then substring
        matched = [t for t in tasks if title_keyword.lower() == t["title"].lower()]
        if not matched:
            matched = [t for t in tasks if title_keyword.lower() in t["title"].lower()]
        
        if not matched:
            # Show available tasks for debugging
            available = ", ".join([f"'{t['title']}'" for t in tasks[:5]])
            return f"❌ No task found matching '{title_keyword}'. Available: {available}"

        task = matched[0]
        task["status"] = "completed"
        
        # Update the task in Google Tasks
        update_result = service.tasks().update(
            tasklist=list_id, task=task["id"], body=task
        ).execute()
        
        if update_result.get("status") == "completed":
            return f"✅ Marked done: {task['title']}"
        else:
            return f"✅ Updated: {task['title']} (Status: {update_result.get('status', 'unknown')})"

    except HttpError as e:
        return f"❌ Error completing task: {str(e)[:100]}"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"




def delete_task(title_keyword: str) -> str:
    """Delete a task by keyword matching."""
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(tasklist=list_id).execute()
        tasks  = result.get("items", [])

        # Try exact match first, then substring
        matched = [t for t in tasks if title_keyword.lower() == t["title"].lower()]
        if not matched:
            matched = [t for t in tasks if title_keyword.lower() in t["title"].lower()]
        
        if not matched:
            return f"❌ No task found matching '{title_keyword}'."

        task = matched[0]
        service.tasks().delete(tasklist=list_id, task=task["id"]).execute()
        
        return f"🗑️ Task deleted: {task['title']}"

    except HttpError as e:
        return f"❌ Error deleting task: {e}"
    except Exception as e:
        return f"❌ Error: {e}"


def clear_completed_tasks() -> str:
    """Delete all completed tasks."""
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(tasklist=list_id, showCompleted=True).execute()
        tasks  = result.get("items", [])

        completed = [t for t in tasks if t.get("status") == "completed"]
        
        if not completed:
            return "✨ No completed tasks to clear."
        
        count = 0
        for task in completed:
            service.tasks().delete(tasklist=list_id, task=task["id"]).execute()
            count += 1
        
        return f"🧹 Cleared {count} completed task(s)."

    except HttpError as e:
        return f"❌ Error clearing tasks: {e}"
    except Exception as e:
        return f"❌ Error: {e}"


def get_task_stats() -> str:
    """Get statistics about tasks."""
    try:
        service  = _get_service()
        list_id  = _get_default_tasklist(service)

        result = service.tasks().list(tasklist=list_id, showCompleted=True).execute()
        tasks  = result.get("items", [])
        
        if not tasks:
            return "📊 Task Stats: No tasks yet."
        
        total = len(tasks)
        completed = len([t for t in tasks if t.get("status") == "completed"])
        pending = total - completed
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return (
            f"📊 Task Statistics:\n"
            f"  📋 Total tasks: {total}\n"
            f"  🔵 Pending: {pending}\n"
            f"  ✅ Completed: {completed}\n"
            f"  📈 Completion rate: {completion_rate:.1f}%"
        )

    except HttpError as e:
        return f"❌ Error getting stats: {e}"
    except Exception as e:
        return f"❌ Error: {e}"