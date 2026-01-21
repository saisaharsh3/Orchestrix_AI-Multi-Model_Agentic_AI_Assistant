from core.orchestrator import generate_response
from rag.vector_store import PDFVectorStore


try:
    from services.voice import listen, speak
    VOICE_AVAILABLE = True
except Exception:
    VOICE_AVAILABLE = False


def main():
    model = "local"        
    use_web = True 
    use_pdf = False 
    use_voice = False

    pdf_store = PDFVectorStore()

    print("=== AI Assistant (Terminal Mode) ===\n")
    print("Commands:")
    print("  /api               → Switch to Gemini API")
    print("  /local             → Switch to Local Ollama model")
    print("  /loadpdf <name>    → Load PDF from pdfs/")
    print("  /rag on | off      → Enable/Disable PDF RAG")
    print("  /web on | off      → Enable/Disable Web search")
    print("  /voice on | off    → Enable/Disable Voice mode")
    print("  exit / quit        → Quit\n")

    while True:
        print(
            f"\n[Model: {model.upper()} | "
            f"Web: {'ON' if use_web else 'OFF'} | "
            f"PDF: {'ON' if use_pdf else 'OFF'} | "
            f"Voice: {'ON' if use_voice else 'OFF'}]"
        )

        
        if use_voice and VOICE_AVAILABLE:
            print(" Listening...")
            user = listen()
            if not user:
                print(" Could not understand voice input")
                continue
            user = user.strip()
            print(f"You (voice): {user}")
        else:
            user = input("You: ").strip()

        if not user:
            continue

        user_lower = user.lower()

        
        if user_lower in {"exit", "quit", "stop"}:
            print(" Goodbye!")
            break

        
        if use_voice and user_lower in {
            "voice off",
            "turn voice off",
            "disable voice",
            "stop voice",
        }:
            use_voice = False
            print(" Voice mode disabled → text input active")
            continue

        
        if user == "/help":
            print("""
Commands:
/api               → Switch to Gemini API
/local             → Switch to Local Ollama model
/loadpdf <name>    → Load PDF from pdfs/
/rag on | off      → Enable/Disable PDF RAG
/web on | off      → Enable/Disable Web search
/voice on | off    → Enable/Disable Voice mode
exit / quit        → Quit
""")
            continue

        
        if user == "/api":
            model = "api"
            print(" Switched to API model")
            continue

        if user == "/local":
            model = "local"
            print(" Switched to LOCAL model")
            continue

        
        if user.startswith("/rag"):
            try:
                _, state = user.split(maxsplit=1)
                use_pdf = state.lower() == "on"
                print(f" PDF RAG {'enabled' if use_pdf else 'disabled'}")
            except ValueError:
                print(" Usage: /rag on | off")
            continue

        
        if user.startswith("/web"):
            try:
                _, state = user.split(maxsplit=1)
                use_web = state.lower() == "on"
                print(f" Web search {'enabled' if use_web else 'disabled'}")
            except ValueError:
                print(" Usage: /web on | off")
            continue

        
        if user.startswith("/voice"):
            if not VOICE_AVAILABLE:
                print(" Voice dependencies not installed")
                continue
            try:
                _, state = user.split(maxsplit=1)
                use_voice = state.lower() == "on"
                print(f"🎙 Voice mode {'enabled' if use_voice else 'disabled'}")
            except ValueError:
                print(" Usage: /voice on | off")
            continue

        
        if user.startswith("/loadpdf"):
            filename = user.replace("/loadpdf", "").strip()
            if not filename:
                print(" Please specify a PDF filename")
                continue
            try:
                print(f" Loading PDF: pdfs/{filename}")
                count = pdf_store.load_pdf(filename)
                print(f" PDF loaded successfully ({count} chunks indexed)")
            except Exception as e:
                print(" PDF load error:", e)
            continue

        
        try:
            print("\nAssistant is thinking...\n")

            response = generate_response(
                user_input=user,
                model_type=model,
                pdf_store=pdf_store if use_pdf else None,
                use_web=use_web,
            )

            print("Assistant:", response)

            if use_voice and VOICE_AVAILABLE:
                speak(response)

        except Exception as e:
            print("❌ Error:", e)


if __name__ == "__main__":
    main()
