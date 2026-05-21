"""
google_tasks_intent.py - Intent detector for Google Tasks requests
Detects: show tasks, add task, complete task, delete task, list tasks
"""

import re


def detect_tasks_intent(user_input: str) -> dict | None:
    """
    Detect task-related intents from user input.
    
    Returns:
        dict with type, parameters
        None if not a task request
    """
    lower = user_input.lower()
    
    # ─── CLEAR COMPLETED TASKS (CHECK FIRST) ───────────────────────
    if any(phrase in lower for phrase in ["clear completed", "clear done", "clear finished", "clean up tasks", "archive completed"]):
        return {
            "type": "clear_completed"
        }
    
    # ─── TASK STATISTICS ───────────────────────────────────────────
    if any(phrase in lower for phrase in ["task stats", "task statistics", "how many tasks", "task progress", "show stats"]):
        return {
            "type": "task_stats"
        }
    
    # ─── SHOW/LIST TASKS ───────────────────────────────────────────
    if any(phrase in lower for phrase in [
        "show tasks", "list tasks", "show my tasks", "all tasks",
        "what are my tasks", "what tasks", "my tasks", "task list",
        "tasks for today", "pending tasks"
    ]):
        show_completed = "completed" in lower or "done" in lower
        return {
            "type": "list_tasks",
            "show_completed": show_completed
        }
    
    # ─── ADD TASK ───────────────────────────────────────────────────
    # Patterns: "add task ...", "add ... task", "new task ...", "create task ..."
    add_keywords = ["add task", "add a task", "new task", "create task", "remind me to"]
    
    if any(keyword in lower for keyword in add_keywords):
        # Extract task title
        task_title = extract_task_title(user_input, add_keywords)
        
        # Check for due date
        due_date = extract_due_date(user_input)
        
        if task_title:
            return {
                "type": "add_task",
                "title": task_title,
                "due": due_date,
                "notes": ""
            }
    
    # ─── COMPLETE/MARK TASK DONE ───────────────────────────────────
    complete_keywords = ["complete task", "mark done", "mark as done", "did", "finish task"]
    
    # Special handling for "mark [task] as done" / "mark [task] task done" / "mark [task] done" patterns
    if lower.startswith("mark "):
        # Try "mark X as done" pattern
        match = re.search(r"mark\s+(.+?)\s+as\s+done", lower)
        if match:
            task_keyword = match.group(1).strip()
            if task_keyword:
                return {
                    "type": "complete_task",
                    "keyword": task_keyword
                }
        
        # Try "mark X task done" pattern
        match = re.search(r"mark\s+(.+?)\s+task\s+done", lower)
        if match:
            task_keyword = match.group(1).strip()
            if task_keyword:
                return {
                    "type": "complete_task",
                    "keyword": task_keyword
                }
        
        # Try "mark X done" pattern
        match = re.search(r"mark\s+(.+?)\s+done", lower)
        if match:
            task_keyword = match.group(1).strip()
            if task_keyword:
                return {
                    "type": "complete_task",
                    "keyword": task_keyword
                }
    
    if any(keyword in lower for keyword in complete_keywords):
        task_keyword = extract_task_keyword(user_input, complete_keywords)
        
        if task_keyword:
            return {
                "type": "complete_task",
                "keyword": task_keyword
            }
    
    # ─── DELETE TASK ────────────────────────────────────────────────
    delete_keywords = ["delete task", "remove task", "remove"]
    
    if any(keyword in lower for keyword in delete_keywords):
        task_keyword = extract_task_keyword(user_input, delete_keywords)
        
        if task_keyword:
            return {
                "type": "delete_task",
                "keyword": task_keyword
            }
    
    return None


def extract_task_title(user_input: str, keywords: list) -> str:
    """Extract the task title from input like 'add task buy milk'"""
    lower = user_input.lower()
    
    for keyword in keywords:
        if keyword in lower:
            # Find what comes after the keyword
            idx = lower.find(keyword) + len(keyword)
            remainder = user_input[idx:].strip()
            
            # Stop at punctuation or common delimiters
            match = re.search(r"([^.!?;,\n]+)", remainder)
            if match:
                task = match.group(1).strip()
                # Remove date references that might still be there
                task = re.sub(r"\s+(today|tomorrow|next\s+\w+|\d+/\d+|\d+-\d+)", "", task).strip()
                if len(task) > 3:  # Reasonable task length
                    return task
    
    return ""


def extract_task_keyword(user_input: str, keywords: list) -> str:
    """Extract task keyword for completing/deleting"""
    lower = user_input.lower()
    
    for keyword in keywords:
        if keyword in lower:
            idx = lower.find(keyword) + len(keyword)
            remainder = user_input[idx:].strip()
            
            match = re.search(r"([^.!?;,\n]+)", remainder)
            if match:
                keyword = match.group(1).strip()
                if len(keyword) > 0:
                    return keyword
    
    return ""


def extract_due_date(user_input: str) -> str:
    """Extract due date if mentioned"""
    lower = user_input.lower()
    
    # Check for common date patterns
    date_patterns = {
        r"today": "today",
        r"tomorrow": "tomorrow",
        r"next\s+(\w+)": "next week",
        r"(\d{1,2})/(\d{1,2})": "date",
        r"(\d{4})-(\d{2})-(\d{2})": "iso_date",
    }
    
    for pattern, name in date_patterns.items():
        if re.search(pattern, lower):
            # For now, just return a simple format
            # The backend will parse it more robustly
            match = re.search(pattern, user_input)
            if match:
                return match.group(0)
    
    return ""
