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
    
    def search_history(self, query: str, limit: int = 10) -> list:
        """Search conversation history for relevant context."""
        results = []
        query_lower = query.lower()
        
        # ✅ INCREASED from 5 to 10 turns
        for turn in self.current_session[-10:]:  # Last 10 turns, not 5
            user_msg = turn.get("user", "").lower()
            asst_msg = turn.get("assistant", "").lower()
            
            if query_lower in user_msg or query_lower in asst_msg:
                results.append(turn)
        
        return results
    
    def list_history(self) -> str:
        """List all conversations."""
        if not self.conversations:
            return " No conversation history yet."
        
        output = "📚 Conversation History:\n\n"
        for i, session in enumerate(self.conversations[-10:], 1):  # Last 10
            output += f"{i}. **{session['title']}** ({len(session['turns'])} turns)\n"
            output += f"   Started: {session['started'][:10]}\n\n"
        return output

    def get_recent_location_context(self, max_turns: int = 15) -> str:
        """Extract location context from recent conversation."""
        context = ""
        cities = ["hyderabad", "delhi", "bangalore", "mumbai", "pune", "goa", "kolkata", "jaipur", "lucknow", "chandigarh", "ahmedabad", "surat", "pune", "indore", "nagpur"]
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            if any(city in user_msg.lower() for city in cities):
                context += f"User mentioned: {user_msg}\n"
        return context

    def get_recent_email_context(self, max_turns: int = 15) -> dict:
        """Extract email context from recent conversation."""
        import re
        context = {
            "recent_recipients": [],
            "recent_subjects": [],
            "email_tone": "professional",
        }
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "").lower()
            
            # Extract email addresses
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', turn.get("user", ""))
            context["recent_recipients"].extend(emails)
            
            # Extract subject keywords
            if re.search(r"subject|about|regarding", user_msg):
                context["recent_subjects"].append(turn.get("user", ""))
            
            # Detect tone
            if any(t in user_msg for t in ["funny", "humor", "joke", "casual"]):
                context["email_tone"] = "casual"
            elif any(t in user_msg for t in ["formal", "professional", "official"]):
                context["email_tone"] = "professional"
        
        return context

    def get_recent_calendar_context(self, max_turns: int = 15) -> dict:
        """Extract calendar context from recent conversation."""
        import re
        context = {
            "recent_events": [],
            "recent_dates": [],
            "recent_times": [],
        }
        
        # Time patterns
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)',
            r'(?:today|tomorrow|next\s+(?:week|month)|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)',
        ]
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            
            # Extract event keywords
            if any(kw in user_msg.lower() for kw in ["event", "meeting", "appointment", "call", "conference"]):
                context["recent_events"].append(user_msg)
            
            # Extract dates and times
            for pattern in time_patterns:
                matches = re.findall(pattern, user_msg, re.IGNORECASE)
                if matches:
                    context["recent_dates"].extend(matches)
        
        return context

    def get_recent_phone_context(self, max_turns: int = 15) -> dict:
        """Extract phone/contact context from recent conversation."""
        import re
        context = {
            "recent_contacts": [],
            "recent_phone_numbers": [],
            "phone_actions": [],
        }
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "").lower()
            
            # Extract potential contact names (proper nouns after 'call', 'text', 'message')
            if any(kw in user_msg for kw in ["call", "text", "message", "contact", "phone"]):
                context["phone_actions"].append(turn.get("user", ""))
            
            # Extract phone numbers
            phones = re.findall(r'(?:\+\d{1,3}[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', turn.get("user", ""))
            context["recent_phone_numbers"].extend(phones)
            
            # Extract contact names (simple heuristic)
            if re.search(r'\b(?:call|text|message|contact)\s+(\w+)', turn.get("user", ""), re.IGNORECASE):
                matches = re.findall(r'\b(?:call|text|message|contact)\s+(\w+)', turn.get("user", ""), re.IGNORECASE)
                context["recent_contacts"].extend(matches)
        
        return context

    def get_recent_web_context(self, max_turns: int = 15) -> dict:
        """Extract web/automation context from recent conversation."""
        import re
        context = {
            "recent_urls": [],
            "recent_apps": [],
            "recent_searches": [],
        }
        
        apps = ["youtube", "spotify", "whatsapp", "telegram", "instagram", "facebook", "twitter", "Netflix", "chrome", "browser"]
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            user_lower = user_msg.lower()
            
            # Extract URLs
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', user_msg)
            context["recent_urls"].extend(urls)
            
            # Extract app mentions
            for app in apps:
                if app in user_lower:
                    context["recent_apps"].append(app)
            
            # Extract search queries
            if any(kw in user_lower for kw in ["search", "find", "look up", "browse"]):
                context["recent_searches"].append(user_msg)
        
        return context

    def get_recent_weather_context(self, max_turns: int = 15) -> dict:
        """Extract weather context from recent conversation."""
        import re
        context = {
            "locations": [],
            "time_refs": [],
            "weather_keywords": [],
        }
        
        weather_kws = ["weather", "temperature", "rain", "sunny", "cloudy", "forecast", "wind", "humidity", "snow"]
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            user_lower = user_msg.lower()
            
            # Check if weather-related
            if any(kw in user_lower for kw in weather_kws):
                context["weather_keywords"].append(user_msg)
                
                # Extract location (city names)
                cities = ["hyderabad", "delhi", "bangalore", "mumbai", "pune", "goa", "london", "new york", "tokyo"]
                for city in cities:
                    if city in user_lower:
                        context["locations"].append(city)
                
                # Extract time references
                time_refs = ["today", "tomorrow", "week", "month", "now", "later", "evening", "morning", "afternoon"]
                for ref in time_refs:
                    if ref in user_lower:
                        context["time_refs"].append(ref)
        
        return context

    def get_recent_finance_context(self, max_turns: int = 15) -> dict:
        """Extract finance/transaction context from recent conversation."""
        import re
        context = {
            "recent_amounts": [],
            "recent_stocks": [],
            "transaction_keywords": [],
        }
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            user_lower = user_msg.lower()
            
            # Extract amounts
            amounts = re.findall(r'[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?', user_msg)
            context["recent_amounts"].extend(amounts)
            
            # Check for transaction keywords
            if any(kw in user_lower for kw in ["transfer", "send money", "pay", "transaction", "purchase", "buy", "sell", "stock", "investment", "crypto"]):
                context["transaction_keywords"].append(user_msg)
            
            # Extract stock symbols (simple heuristic)
            stocks = re.findall(r'\b[A-Z]{1,5}\b(?:\s+stock)?', user_msg)
            context["recent_stocks"].extend(stocks)
        
        return context

    def get_recent_news_context(self, max_turns: int = 15) -> dict:
        """Extract news/search context from recent conversation."""
        import re
        context = {
            "recent_queries": [],
            "topics": [],
            "keywords": [],
        }
        
        topics = ["sports", "tech", "business", "health", "entertainment", "politics", "world", "india", "breaking", "latest"]
        
        for turn in self.current_session[-max_turns:]:
            user_msg = turn.get("user", "")
            user_lower = user_msg.lower()
            
            # Check for search/news keywords
            if any(kw in user_lower for kw in ["news", "search", "find", "latest", "breaking", "headline"]):
                context["recent_queries"].append(user_msg)
                
                # Extract topics
                for topic in topics:
                    if topic in user_lower:
                        context["topics"].append(topic)
                
                # Extract keywords (simple extraction)
                words = re.findall(r'\b[a-z]{4,}\b', user_lower)
                context["keywords"].extend(words[:5])  # Limit to first 5
        
        return context

    def get_feature_context(self, feature: str, max_turns: int = 15) -> dict:
        """
        Universal method to get context for any feature.
        
        Args:
            feature: One of "maps", "email", "calendar", "phone", "web", "weather", "finance", "news"
            max_turns: Number of recent turns to consider
        
        Returns:
            Dict with relevant context for the feature
        """
        feature_lower = feature.lower()
        
        if feature_lower == "maps":
            return {"location": self.get_recent_location_context(max_turns)}
        elif feature_lower == "email":
            return self.get_recent_email_context(max_turns)
        elif feature_lower == "calendar":
            return self.get_recent_calendar_context(max_turns)
        elif feature_lower in ["phone", "web"]:
            return self.get_recent_phone_context(max_turns)
        elif feature_lower == "weather":
            return self.get_recent_weather_context(max_turns)
        elif feature_lower == "finance":
            return self.get_recent_finance_context(max_turns)
        elif feature_lower == "news":
            return self.get_recent_news_context(max_turns)
        else:
            return {}

# Global instance
conversation_memory = ConversationMemory()