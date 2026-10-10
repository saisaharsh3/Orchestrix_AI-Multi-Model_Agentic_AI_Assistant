"""
rag/vector_store.py - On-device PDF retrieval (FAISS + sentence-transformers).

Each user gets their own store (see core/session.py) so one person's
documents are never used to answer another person's questions.
"""

import json
import os
import threading

import faiss
import numpy as np
from pypdf import PdfReader

from core.logger import get_logger

logger = get_logger(__name__)

# OCR for scanned PDFs is optional. Point these at your installs via .env.
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

try:
    import pytesseract
    from pdf2image import convert_from_path
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        OCR_AVAILABLE = True
    else:
        OCR_AVAILABLE = False
except ImportError:
    OCR_AVAILABLE = False

EMBEDDING_DIM = 384

_embedders: dict = {}
_embedder_lock = threading.Lock()


def _get_embedder(model_name: str):
    """Load each embedding model once per process and share it across stores."""
    with _embedder_lock:
        if model_name not in _embedders:
            from sentence_transformers import SentenceTransformer
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
            _embedders[model_name] = SentenceTransformer(model_name, device=device)
        return _embedders[model_name]


STOPWORDS = {
    "the", "is", "a", "an", "of", "in", "to", "and", "or",
    "what", "how", "who", "when", "where", "was", "are", "it",
    "this", "that", "with", "for", "on", "at", "be", "my", "i",
    # generic summary words that shouldn't drive search
    "give", "me", "brief", "explain", "explanation", "summary",
    "summarize", "about", "tell", "describe", "pdf", "document",
    "file", "contents", "content", "overview", "details",
}

# Queries that mean "give me everything" — return top-N chunks directly
OVERVIEW_PATTERNS = {
    "brief", "summary", "summarize", "overview", "explain",
    "what is this", "what's this", "contents", "about this",
    "tell me about", "describe", "introduction", "what does",
}


class PDFVectorStore:
    def __init__(
        self,
        pdf_dir="pdfs",
        index_path="rag/index.faiss",
        meta_path="rag/chunks.json",
        model_name="all-MiniLM-L6-v2",
        similarity_threshold=0.15,
    ):
        self.pdf_dir             = pdf_dir
        self.index_path          = index_path
        self.meta_path           = meta_path
        self.similarity_threshold = similarity_threshold

        self.embedder = _get_embedder(model_name)

        self.index        = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.text_chunks  = []
        self.loaded_files = set()

        self._load_index()

    def _load_index(self):
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.text_chunks  = data.get("chunks", [])
                    self.loaded_files = set(data.get("loaded_files", []))
                logger.info(f"Loaded FAISS index ({len(self.text_chunks)} chunks)")
        except Exception as e:
            logger.warning(f"Corrupted index ({e}). Rebuilding.")
            self.index        = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.text_chunks  = []
            self.loaded_files = set()

    def _save_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {"chunks": self.text_chunks, "loaded_files": list(self.loaded_files)},
                f, ensure_ascii=False, indent=2,
            )

    def clear(self):
        self.index        = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.text_chunks  = []
        self.loaded_files = set()
        for path in (self.index_path, self.meta_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.warning(f"Could not remove {path}: {e}")
        logger.info("PDF store cleared.")

    def _extract_text(self, path: str) -> list[str]:
        reader     = PdfReader(path)
        page_texts = []
        ocr_warned = False

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                page_texts.append(text.strip())
            else:
                if OCR_AVAILABLE:
                    logger.info(f"Page {page_num+1} has no text layer, running OCR")
                    try:
                        kwargs = {}
                        if POPPLER_PATH and os.path.exists(POPPLER_PATH):
                            kwargs["poppler_path"] = POPPLER_PATH
                        images = convert_from_path(
                            path, first_page=page_num+1,
                            last_page=page_num+1, dpi=300, **kwargs,
                        )
                        for img in images:
                            ocr_text = pytesseract.image_to_string(img, lang="eng")
                            if ocr_text.strip():
                                page_texts.append(ocr_text.strip())
                    except Exception as e:
                        logger.warning(f"OCR failed on page {page_num+1}: {e}")
                else:
                    if not ocr_warned:
                        logger.warning("Scanned page detected but OCR is not available")
                        ocr_warned = True

        return page_texts

    def load_pdf(self, filename: str) -> int:
        if filename in self.loaded_files:
            raise ValueError(f"'{filename}' already indexed. Use /clearpdf to reload.")

        filename = os.path.basename(filename)
        path = os.path.join(self.pdf_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        page_texts = self._extract_text(path)
        if not page_texts:
            raise ValueError("No text could be extracted. PDF may be fully scanned.")

        chunks = []
        for text in page_texts:
            chunks.extend(self._split_text(text))

        if not chunks:
            raise ValueError("Text extracted but produced no usable chunks.")

        logger.info(f"Extracted {len(chunks)} chunks from '{filename}'")

        embeddings = self.embedder.encode(
            chunks, normalize_embeddings=True, show_progress_bar=False,
        )

        self.index.add(np.array(embeddings).astype("float32"))
        self.text_chunks.extend(chunks)
        self.loaded_files.add(filename)
        self._save_index()
        return len(chunks)

    # ── Semantic search ───────────────────────────────────────────────────
    def search(self, query: str, top_k: int = 8) -> list[str]:
        if self.index.ntotal == 0:
            return []

        query_vec = self.embedder.encode(
            [query], normalize_embeddings=True
        ).astype("float32")

        scores, indices = self.index.search(query_vec, top_k)

        return [
            self.text_chunks[idx]
            for score, idx in zip(scores[0], indices[0], strict=False)
            if idx < len(self.text_chunks) and score >= self.similarity_threshold
        ]

    # ── Detect if query is a generic overview request ─────────────────────
    def _is_overview_query(self, query: str) -> bool:
        q = query.lower()
        return any(pattern in q for pattern in OVERVIEW_PATTERNS)

    # ── Hybrid search with generic-query fallback ─────────────────────────
    def smart_search(self, query: str, top_k: int = 12) -> list[str]:
        if self.index.ntotal == 0:
            return []

        # ── Generic overview query → return first N chunks (document start)
        if self._is_overview_query(query):
            semantic = self.search(query, top_k=top_k)
            # Blend: first few chunks (intro) + semantic hits
            intro_chunks = self.text_chunks[:3]
            combined = []
            seen = set()
            for chunk in intro_chunks + semantic:
                if chunk not in seen:
                    combined.append(chunk)
                    seen.add(chunk)
            return combined[:top_k]

        # ── Specific query → semantic + lexical hybrid ────────────────────
        semantic_hits = self.search(query, top_k=top_k)

        words = set(query.lower().split()) - STOPWORDS
        lexical_hits = []
        if words:
            lexical_hits = [
                chunk for chunk in self.text_chunks
                if any(w in chunk.lower() for w in words)
            ]

        # Deduplicate while preserving order
        combined = []
        seen = set()
        for chunk in semantic_hits + lexical_hits:
            if chunk not in seen:
                combined.append(chunk)
                seen.add(chunk)

        # ── Last resort: if still empty, return first 5 chunks ────────────
        if not combined:
            return self.text_chunks[:5]

        return combined[:top_k]

    # ── Chunking with overlap ─────────────────────────────────────────────
    def _split_text(self, text, chunk_size=800, overlap=120):
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += chunk_size - overlap
        return chunks
