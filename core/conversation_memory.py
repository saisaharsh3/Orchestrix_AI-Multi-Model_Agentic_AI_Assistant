"""
conversation_memory.py - Multi-turn conversation tracking
"""

import json
import os
from datetime import datetime

HISTORY_FILE = "memory/conversation_history.json"

class ConversationMemory:
    def __init__(self):
        self.conversations = self._load_history()
        self.current_session = []
    
    def _load_history(self) -> list:
        """Load conversation history from disk."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save conversation history to disk."""
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.conversations, f, indent=2)
    
    def add_turn(self, user_input: str, assistant_response: str):
        """Add a user-assistant turn to current session."""
        self.current_session.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response,
        })
    
    def save_session(self, title: str = None):
        """Save current session to history."""
        if not self.current_session:
            return
        
        session = {
            "title": title or f"Conversation {len(self.conversations) + 1}",
            "started": self.current_session[0]["timestamp"],
            "turns": self.current_session,
        }
        self.conversations.append(session)
        self._save_history()
        self.current_session = []
    
    def search_history(self, query: str) -> str:
        """Search conversation history."""
        results = []
        for session in self.conversations:
            for turn in session["turns"]:
                if query.lower() in turn["user"].lower() or query.lower() in turn["assistant"].lower():
                    results.append({
                        "session": session["title"],
                        "user": turn["user"],
                        "assistant": turn["assistant"][:200] + "..." if len(turn["assistant"]) > 200 else turn["assistant"],
                    })
        
        if not results:
            return " No matching conversations found."
        
        output = f"📚 Found {len(results)} matching turns:\n\n"
        for i, r in enumerate(results[:5], 1):
            output += f"{i}. **{r['session']}**\n"
            output += f"   You: {r['user'][:100]}...\n"
            output += f"   Bot: {r['assistant']}\n\n"
        return output
    
    def list_history(self) -> str:
        """List all conversations."""
        if not self.conversations:
            return " No conversation history yet."
        
        output = "📚 Conversation History:\n\n"
        for i, session in enumerate(self.conversations[-10:], 1):  # Last 10
            output += f"{i}. **{session['title']}** ({len(session['turns'])} turns)\n"
            output += f"   Started: {session['started'][:10]}\n\n"
        return output

# Global instance
conversation_memory = ConversationMemory()