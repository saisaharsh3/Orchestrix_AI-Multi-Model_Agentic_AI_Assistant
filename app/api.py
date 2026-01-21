from fastapi import FastAPI, UploadFile, File, Form
from core.orchestrator import generate_response
from services.speech_to_text import stt

app = FastAPI(title="AI Assistant API")

@app.post("/chat")
async def chat(
    message: str = Form(...),
    model_type: str = Form("api")  # "api" or "local"
):
    answer = generate_response(message, model_type=model_type)
    return {
        "success": True,
        "answer": answer
    }

@app.post("/speech")
async def speech(
    audio: UploadFile = File(...),
    model_type: str = Form("api")
):
    text = stt(audio)
    answer = generate_response(text, model_type=model_type)
    return {
        "success": True,
        "transcript": text,
        "answer": answer
    }
