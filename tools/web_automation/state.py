# tools/web_automation/state.py
WEB_STATE = {
    "active": False,
    "task": None,              # youtube | movie
    "step": None,              # ask_date | ask_time | confirm
    "data": {
        "movie": None,
        "date": None,
        "time": None,
        "seats": "best"
    }
}

def reset_web_state():
    WEB_STATE["active"] = False
    WEB_STATE["task"] = None
    WEB_STATE["step"] = None
    WEB_STATE["data"].clear()
