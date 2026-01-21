WEB_STATE = {
    "active": False,
    "type": None,
    "step": None,
    "data": {}
}


def reset_web_state():
    WEB_STATE["active"] = False
    WEB_STATE["type"] = None
    WEB_STATE["step"] = None
    WEB_STATE["data"] = {}
