"""
services/voice.py - Microphone input and spoken output for the terminal UI.

Optional: pip install -r requirements-voice.txt
"""

import os
import tempfile

from core.logger import get_logger

logger = get_logger(__name__)

_engine = None


def speak(text: str) -> None:
    global _engine
    import pyttsx3

    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 180)
    _engine.say(text)
    _engine.runAndWait()


def listen(duration: int = 5, samplerate: int = 16000) -> str:
    """Record `duration` seconds from the microphone and return the transcript ('' on failure)."""
    import sounddevice as sd
    import soundfile as sf
    import speech_recognition as sr

    print(" Listening...")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()

    fd, filename = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        sf.write(filename, audio, samplerate)
        recognizer = sr.Recognizer()
        with sr.AudioFile(filename) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except (sr.UnknownValueError, sr.RequestError) as e:
        logger.warning(f"Speech recognition failed: {e}")
        return ""
    finally:
        os.unlink(filename)
