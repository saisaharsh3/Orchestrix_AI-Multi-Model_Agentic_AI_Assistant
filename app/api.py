"""
app/api.py - HTTP API.

Run:  uvicorn app.api:app --host 127.0.0.1 --port 8000

Authentication: send `Authorization: Bearer <ORCHESTRIX_API_TOKEN>`.
If ORCHESTRIX_API_TOKEN is not set, only requests from localhost are accepted.
"""

import hmac
import os
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile

from config.settings import settings
from core.orchestrator import respond

app = FastAPI(title="Orchestrix API")

_LOCALHOST = {"127.0.0.1", "::1", "localhost"}


def require_auth(request: Request) -> None:
    if settings.API_TOKEN:
        header = request.headers.get("authorization", "")
        token = header.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, settings.API_TOKEN):
            raise HTTPException(status_code=401, detail="Invalid or missing API token")
    elif not request.client or request.client.host not in _LOCALHOST:
        raise HTTPException(status_code=403, detail="Set ORCHESTRIX_API_TOKEN to allow remote access")


def _validate_model(model_type: str | None) -> str | None:
    if model_type not in (None, "", "api", "local"):
        raise HTTPException(status_code=422, detail="model_type must be 'api' or 'local'")
    return model_type or None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", dependencies=[Depends(require_auth)])
def chat(
    message: str = Form(...),
    model_type: str | None = Form(None),
    user_id: str = Form("api"),
):
    reply = respond(message, user_id=f"api:{user_id}", model_type=_validate_model(model_type))
    return {"success": True, "answer": reply.text}


@app.post("/speech", dependencies=[Depends(require_auth)])
def speech(
    audio: UploadFile = File(...),
    model_type: str | None = Form(None),
    user_id: str = Form("api"),
):
    try:
        from tools.voice_tool import transcribe_audio
    except ImportError as e:
        raise HTTPException(status_code=501, detail="Voice support is not installed") from e

    suffix = Path(audio.filename or "audio.ogg").suffix or ".ogg"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio.file.read())
        text = transcribe_audio(path)
    finally:
        Path(path).unlink(missing_ok=True)

    if text.startswith("Error"):
        raise HTTPException(status_code=422, detail=text)
    reply = respond(text, user_id=f"api:{user_id}", model_type=_validate_model(model_type))
    return {"success": True, "transcript": text, "answer": reply.text}
