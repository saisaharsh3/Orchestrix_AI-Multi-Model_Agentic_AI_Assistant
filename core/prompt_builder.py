

from datetime import datetime


def build_rag_prompt(query: str, chunks: list[str], model_type: str) -> str:
    """
    Build a RAG prompt optimised for the model type.
    Local models get a tighter, instruction-tuned format.
    API models get the full structured format.
    """
    today        = datetime.now().strftime("%B %d, %Y")
    context_text = "\n\n".join(
        f"[{i+1}] {chunk}" for i, chunk in enumerate(chunks)
    )

    if model_type == "local":
        # llama3 via Ollama chat API — the system prompt is set in local_llm.py
        # so here we just format the user message content cleanly
        return (
            f"Here are excerpts from a document:\n\n"
            f"{context_text}\n\n"
            f"Based ONLY on the above excerpts, answer this question:\n"
            f"{query}\n\n"
            f"If the answer is not in the excerpts, say so clearly. Do not guess."
        )

    else:
        # Full structured prompt for API models
        return f"""You are a document Q&A assistant. Answer using ONLY the PDF chunks below.

RULES:
1. Base your answer ENTIRELY on the chunks — no outside knowledge.
2. Reference chunk numbers where helpful e.g. [1], [2].
3. If the answer is not in any chunk, say: "Not found in the PDF."
4. Be clear and well-structured.

DATE: {today}

PDF CONTENT:
{context_text}

QUESTION: {query}

ANSWER:"""


def build_general_prompt(query: str, context_blocks: list[str], model_type: str) -> str:
    """
    Build a general (non-RAG) prompt optimised for model type.
    """
    today   = datetime.now().strftime("%B %d, %Y")
    context = "\n\n".join(context_blocks)

    if model_type == "local":
        ctx_block = (context + "\n\n") if context else ""
        return (
            f"{ctx_block}"
            f"{query}"
        )

    else:
        return f"""You are a helpful AI assistant.

DATE: {today}

{context}

QUESTION: {query}

ANSWER:""".strip()


def build_web_prompt(query: str, news: list[str], web: list[str], model_type: str) -> str:
    """
    Build a web-search-grounded prompt.
    """
    today = datetime.now().strftime("%B %d, %Y")
    parts = []
    if news:
        parts.append("NEWS:\n" + "\n".join(news))
    if web:
        parts.append("WEB RESULTS:\n" + "\n".join(web))
    context = "\n\n".join(parts)

    if model_type == "local":
        return (
            f"{context}\n\n"
            f"{query}"
        )

    else:
        return f"""You are a helpful AI assistant. Today is {today}.

{context}

QUESTION: {query}

ANSWER:""".strip()