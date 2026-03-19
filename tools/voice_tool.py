"""
voice_tool.py - Voice message transcription using local Whisper
Install: pip install openai-whisper
And system ffmpeg: https://ffmpeg.org/download.html (add to PATH)
"""

import os
import tempfile
import subprocess

# Add ffmpeg to PATH explicitly for Windows
FFMPEG_DIRS = [
    r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin",
    r"C:\ffmpeg-8.0.1-essentials_build\bin",
    r"C:\ffmpeg\bin",
    r"C:\Program Files\ffmpeg\bin",
]
for ffmpeg_dir in FFMPEG_DIRS:
    if os.path.exists(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"ffmpeg path set: {ffmpeg_dir}")
        break

WHISPER_AVAILABLE = False
whisper_model     = None

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass

WHISPER_MODEL_SIZE = "base"


def _load_model():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model (first time only)...")
        whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        print("Whisper model loaded.")
    return whisper_model


def transcribe_audio(file_path: str) -> str:
    if not WHISPER_AVAILABLE:
        return (
            "Error: Whisper not installed.\n"
            "Run: pip install openai-whisper\n"
            "And install ffmpeg from: https://ffmpeg.org/download.html"
        )

    if not os.path.exists(file_path):
        return f"Error: Audio file not found: {file_path}"

    # Verify ffmpeg is accessible
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return (
                "Error: ffmpeg not working.\n"
                "Make sure ffmpeg is installed at C:\\ffmpeg-8.0.1-essentials_build\\bin"
            )
    except FileNotFoundError:
        return (
            "Error: ffmpeg not found.\n"
            "Add C:\\ffmpeg-8.0.1-essentials_build\\bin to your PATH\n"
            "Then restart the bot."
        )

    try:
        model  = _load_model()
        result = model.transcribe(file_path, language="en")
        text   = result.get("text", "").strip()
        if not text:
            return "Error: Could not transcribe audio. File may be silent or corrupted."
        return text
    except Exception as e:
        if "ffmpeg" in str(e).lower():
            return (
                "Error: ffmpeg not found.\n"
                "Download from https://ffmpeg.org/download.html and add to PATH."
            )
        return f"Error transcribing audio: {e}"


def transcribe_bytes(audio_bytes: bytes, suffix: str = ".ogg") -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        result = transcribe_audio(tmp_path)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return result
    except Exception as e:
        return f"Error: {e}"