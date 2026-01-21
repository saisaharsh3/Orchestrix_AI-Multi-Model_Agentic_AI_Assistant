import speech_recognition as sr
import pyttsx3
import sounddevice as sd
import soundfile as sf
import tempfile
import os

engine = pyttsx3.init()
engine.setProperty("rate", 180)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def listen(duration=5, samplerate=16000):
    print(" Listening...")

    audio = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="int16"
    )
    sd.wait()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        sf.write(f.name, audio, samplerate)
        filename = f.name

    r = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio_data = r.record(source)

    os.unlink(filename)

    try:
        text = r.recognize_google(audio_data)
        print(f"You (voice): {text}")
        return text
    except:
        return ""
