from core.orchestrator import generate_response
from rag.vector_store import PDFVectorStore

try:
    from services.voice import listen, speak
    VOICE_AVAILABLE = True
except Exception:
    VOICE_AVAILABLE = False


def main():
    model   = "local"
    use_web = True
    use_pdf = False
    use_voice = False

    pdf_store = PDFVectorStore()

    print("=== Orchestrix AI (Terminal Mode) ===\n")

    while True:
        print(
            f"\n[Model: {model.upper()} | "
            f"Web: {'ON' if use_web else 'OFF'} | "
            f"PDF: {'ON' if use_pdf else 'OFF'} | "
            f"Voice: {'ON' if use_voice else 'OFF'}]"
        )

        user = input("You: ").strip()
        if not user:
            continue

        user_lower = user.lower()

        if user_lower in {"exit", "quit"}:
            print(" Goodbye!")
            break

        if user == "/api":
            model = "api"
            print(" Switched to API model")
            continue

        if user == "/local":
            model = "local"
            print(" Switched to LOCAL model")
            continue

        if user.startswith("/web"):
            use_web = "on" in user_lower
            print(f" Web search {'enabled' if use_web else 'disabled'}")
            continue

        if user.startswith("/rag"):
            use_pdf = "on" in user_lower
            print(f" PDF RAG {'enabled' if use_pdf else 'disabled'}")
            continue

        if user.startswith("/loadpdf"):
            filename = user.replace("/loadpdf", "").strip()
            try:
                count = pdf_store.load_pdf(filename)
                print(f" PDF loaded ({count} chunks indexed)")
            except Exception as e:
                print(" PDF load error:", e)
            continue

        if user == "/clearpdf":
            # FIX: use proper .clear() method instead of accessing internals
            pdf_store.clear()
            print(" PDF memory cleared")
            continue

        if user == "/help":
            print(
                "\n Commands:\n"
                "  /api       — switch to API model\n"
                "  /local     — switch to local model\n"
                "  /web on|off\n"
                "  /rag on|off\n"
                "  /loadpdf <filename>\n"
                "  /clearpdf\n"
                "  exit / quit\n\n"
                " Phone (ADB required):\n"
                "  open youtube, search youtube for <query>\n"
                "  open spotify, play <song> on spotify\n"
                "  call <number>, navigate to <place>\n"
                "  set alarm for HH:MM, set timer for Xm\n"
                "  volume up/down, set volume to X%\n"
                "  set brightness to X%\n"
                "  open camera, take screenshot\n"
                "  connect phone <ip>\n"
            )
            continue

        print("\nAssistant is thinking...\n")
        try:
            response = generate_response(
                user_input=user,
                model_type=model,
                pdf_store=pdf_store,   # always pass store; orchestrator checks use_pdf flag
                use_web=use_web,
                use_pdf=use_pdf,       # FIX: was never passed before
            )
            print("Assistant:", response)
        except Exception as e:
            print(" Error:", e)


if __name__ == "__main__":
    main()