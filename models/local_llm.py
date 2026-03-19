import ollama

MODEL = "llama3:8b-instruct-q4_K_M"

SYSTEM_PROMPT = """You are Orchestrix AI, a concise and accurate assistant.

Rules you must always follow:
- Answer in 1-3 short sentences unless more detail is needed.
- Never start with "I apologize", "Certainly!", "Of course!", "Based on the provided content".
- If asked to do a specific action like adding a task or setting a reminder, confirm it simply.
- Do not explain what you could do — just do it or say you cannot.
- If you don't know something, say "I don't know" — do not guess."""

RAG_SYSTEM_PROMPT = """You are a document Q&A assistant.
Answer ONLY using the document content provided.
If the answer is not in the document, say exactly: "Not found in the document."
Never guess or add outside knowledge."""


def local_generate(prompt: str) -> str:
    try:
        res = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            options={
                "temperature":    0.3,
                "top_p":          0.9,
                "repeat_penalty": 1.2,
                "num_gpu":        20,
            },
        )
        return res["message"]["content"].strip()
    except Exception as e:
        if "CUDA" in str(e) or "500" in str(e):
            return _cpu_fallback(prompt, SYSTEM_PROMPT)
        return f"Local model error: {e}"


def local_generate_rag(prompt: str) -> str:
    try:
        res = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            options={
                "temperature":    0.1,
                "top_p":          0.8,
                "repeat_penalty": 1.2,
                "num_gpu":        20,
            },
        )
        return res["message"]["content"].strip()
    except Exception as e:
        if "CUDA" in str(e) or "500" in str(e):
            return _cpu_fallback(prompt, RAG_SYSTEM_PROMPT)
        return f"Local model error: {e}"


def _cpu_fallback(prompt: str, system: str) -> str:
    try:
        print("CUDA error — retrying on CPU...")
        res = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            options={"temperature": 0.3, "num_gpu": 0},
        )
        return res["message"]["content"].strip()
    except Exception as e:
        return f"Local model error (CPU fallback failed): {e}"