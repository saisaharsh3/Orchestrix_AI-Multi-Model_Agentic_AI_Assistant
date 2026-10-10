"""Google Tasks."""

from core.handlers.base import Reply, Request
from tools.google_tasks_intent import detect_tasks_intent
from tools.google_tasks_tool import (
    add_task,
    clear_completed_tasks,
    complete_task,
    delete_task,
    get_task_stats,
    list_tasks,
)


def handle(req: Request) -> Reply | None:
    intent = detect_tasks_intent(req.text)
    if not intent:
        return None
    kind = intent.get("type")
    confidence = intent.get("confidence", 0.85)

    def reply(text: str) -> Reply:
        return Reply(text, confidence=confidence)

    if kind == "list_tasks":
        return reply(list_tasks(show_completed=intent.get("show_completed", False)))

    if kind == "add_task":
        title = intent.get("title", "").strip()
        if not title:
            return reply("What task do you want to add?")
        return reply(add_task(title, due=intent.get("due", "").strip()))

    if kind == "complete_task":
        keyword = intent.get("keyword", "").strip()
        return reply(complete_task(keyword) if keyword else "Which task did you complete?")

    if kind == "delete_task":
        keyword = intent.get("keyword", "").strip()
        return reply(delete_task(keyword) if keyword else "Which task do you want to delete?")

    if kind == "clear_completed":
        return reply(clear_completed_tasks())

    if kind == "task_stats":
        return reply(get_task_stats())

    return None
