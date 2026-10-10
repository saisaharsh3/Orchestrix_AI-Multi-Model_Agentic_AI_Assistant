"""
main.py - Terminal interface for Orchestrix.

Run: python main.py
"""

from core.orchestrator import respond
from core.session import sessions

USER_ID = "cli"

HELP = (
    "\nCommands:\n"
    "  /api       — switch to API model (Gemini)\n"
    "  /local     — switch to local model (Ollama)\n"
    "  /web on|off\n"
    "  /rag on|off\n"
    "  /loadpdf <path-or-filename>\n"
    "  /clearpdf\n"
    "  /voice     — speak one message (needs requirements-voice.txt)\n"
    "  exit / quit\n\n"
    "Type /help for everything the assistant can do."
)


def _load_pdf(session, arg: str) -> None:
    import shutil
    from pathlib import Path

    src = Path(arg)
    if src.exists():
        dest = session.pdf_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy(src, dest)
        name = src.name
    else:
        name = arg  # already in the user's PDF folder
    try:
        count = session.pdf_store.load_pdf(name)
        session.use_pdf = True
        session.recent_pdfs = (session.recent_pdfs + [str(session.pdf_dir / name)])[-2:]
        print(f" PDF loaded ({count} chunks indexed). RAG is ON.")
    except Exception as e:
        print(" PDF load error:", e)


def _voice_input() -> str | None:
    try:
        from services.voice import listen
    except Exception as e:
        print(f" Voice unavailable: {e}")
        return None
    return listen() or None


def main():
    session = sessions.get(USER_ID)
    print("=== Orchestrix AI (Terminal Mode) ===  (type 'commands' for options)\n")

    while True:
        print(
            f"\n[Model: {session.model_type.upper()} | "
            f"Web: {'ON' if session.use_web else 'OFF'} | "
            f"PDF: {'ON' if session.use_pdf else 'OFF'}]"
        )
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n Goodbye!")
            break
        if not user:
            continue
        lower = user.lower()

        if lower in {"exit", "quit"}:
            print(" Goodbye!")
            break
        if lower == "commands":
            print(HELP)
            continue
        if lower in {"/api", "/local"}:
            session.model_type = lower[1:]
            print(f" Switched to {session.model_type.upper()} model")
            continue
        if lower.startswith("/web"):
            session.use_web = lower.endswith("on")
            print(f" Web search {'enabled' if session.use_web else 'disabled'}")
            continue
        if lower.startswith("/rag"):
            session.use_pdf = lower.endswith("on")
            print(f" PDF RAG {'enabled' if session.use_pdf else 'disabled'}")
            continue
        if lower.startswith("/loadpdf"):
            _load_pdf(session, user[len("/loadpdf"):].strip())
            continue
        if lower == "/clearpdf":
            session.pdf_store.clear()
            session.recent_pdfs = []
            session.use_pdf = False
            print(" PDF memory cleared")
            continue
        if lower == "/voice":
            user = _voice_input()
            if not user:
                continue
            print(f"You (voice): {user}")

        print("\nAssistant is thinking...\n")
        reply = respond(user, user_id=USER_ID)
        print("Assistant:", reply.text)
        for path in reply.files:
            print(f" File saved: {path}")


if __name__ == "__main__":
    main()
