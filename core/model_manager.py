from models.local_llm import local_generate, local_generate_rag
from models.gemini_llm import gemini_generate

# If these strings appear in the prompt, use RAG mode (low temperature)
_RAG_SIGNALS = ["document excerpts", "pdf chunks", "pdf content", "[1]", "[2]", "[3]"]

def _is_rag_prompt(prompt: str) -> bool:
    p = prompt.lower()
    return any(sig.lower() in p for sig in _RAG_SIGNALS)

def generate_llm(prompt: str, model_type: str = "api") -> str:
    try:
        if model_type == "local":
            if _is_rag_prompt(prompt):
                return local_generate_rag(prompt)
            return local_generate(prompt)
        else:
            return gemini_generate(prompt)

    except Exception as e:
        # Auto fallback if Gemini quota exhausted
        if "RESOURCE_EXHAUSTED" in str(e):
            print(" API quota exhausted — falling back to local model")
            if _is_rag_prompt(prompt):
                return local_generate_rag(prompt)
            return local_generate(prompt)
        raise e