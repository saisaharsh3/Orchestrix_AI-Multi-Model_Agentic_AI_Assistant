import json
import os

MEMORY_FILE = "memory/chat_history.json"

class Memory:
    def __init__(self):
        os.makedirs("memory", exist_ok=True)
        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "w") as f:
                json.dump([], f)

    def add(self, user, assistant):
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)

        data.append({"user": user, "assistant": assistant})

        with open(MEMORY_FILE, "w") as f:
            json.dump(data[-20:], f, indent=2)

    def get_context(self):
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)

        text = ""
        for item in data:
            text += f"User: {item['user']}\nAssistant: {item['assistant']}\n"
        return text
