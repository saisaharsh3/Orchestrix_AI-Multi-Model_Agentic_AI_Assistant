"""
smart_search.py - Search across all tools
"""

from tools.email_tool import search_emails
from tools.google_drive_tool import search_drive
from tools.google_tasks_tool import list_tasks
from tools.wiki_search import wiki_search


def smart_search(query: str) -> str:
    """
    Search across emails, drive, tasks, and wiki in one go.
    """
    results = {
        "emails": [],
        "drive": [],
        "tasks": [],
        "wiki": None,
    }
    
    try:
        results["emails"] = search_emails(query).split("\n")[:3]  
    except Exception as e:
        results["emails"] = [f"Email search error: {e}"]
    
    try:
        results["drive"] = search_drive(query).split("\n")[:3]
    except Exception as e:
        results["drive"] = [f"Drive search error: {e}"]
    
    try:
        tasks_list = list_tasks()
        if query.lower() in tasks_list.lower():
            results["tasks"] = [l for l in tasks_list.split("\n") if query.lower() in l.lower()][:3]
    except Exception as e:
        results["tasks"] = [f"Task search error: {e}"]
    
    try:
        results["wiki"] = wiki_search(query)
    except Exception as e:
        results["wiki"] = f"Wiki error: {e}"
    
    # Format output
    output = f" Smart Search Results for '{query}':\n\n"
    
    if results["emails"]:
        output += f" Emails:\n" + "\n".join(results["emails"]) + "\n\n"
    
    if results["drive"]:
        output += f" Drive Files:\n" + "\n".join(results["drive"]) + "\n\n"
    
    if results["tasks"]:
        output += f"✓ Tasks:\n" + "\n".join(results["tasks"]) + "\n\n"
    
    if results["wiki"]:
        output += f" Wiki:\n" + results["wiki"]
    
    return output if output.strip() != f" Smart Search Results for '{query}':\n\n" else " No results found."