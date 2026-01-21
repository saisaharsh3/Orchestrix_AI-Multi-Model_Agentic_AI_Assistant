import os
import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader


class PDFVectorStore:
    def __init__(
        self,
        pdf_dir="pdfs",
        index_path="rag/index.faiss",
        meta_path="rag/chunks.pkl",
        model_name="all-MiniLM-L6-v2",
        similarity_threshold=0.45,   # ⬅ LOWERED for better recall
    ):
        self.pdf_dir = pdf_dir
        self.index_path = index_path
        self.meta_path = meta_path
        self.similarity_threshold = similarity_threshold

        #  GPU if available
        self.embedder = SentenceTransformer(
            model_name,
            device="cuda" if self._has_cuda() else "cpu",
        )

        # Cosine similarity (normalized vectors)
        self.index = faiss.IndexFlatIP(384)
        self.text_chunks = []

        self._load_index()

    # ======================================================
    # GPU check
    # ======================================================
    def _has_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    # ======================================================
    # Safe load
    # ======================================================
    def _load_index(self):
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "rb") as f:
                    self.text_chunks = pickle.load(f)
                print(f" Loaded FAISS index ({len(self.text_chunks)} chunks)")
        except Exception:
            print(" Corrupted FAISS index detected. Rebuilding index.")
            self.index = faiss.IndexFlatIP(384)
            self.text_chunks = []

    def _save_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.text_chunks, f)

    # ======================================================
    # PDF ingestion
    # ======================================================
    def load_pdf(self, filename):
        path = os.path.join(self.pdf_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        reader = PdfReader(path)
        chunks = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                page_chunks = self._split_text(text)
                chunks.extend(page_chunks)

        if not chunks:
            raise ValueError("No extractable text found in PDF")

        embeddings = self.embedder.encode(
            chunks,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        self.index.add(np.array(embeddings).astype("float32"))
        self.text_chunks.extend(chunks)

        self._save_index()
        return len(chunks)

    # ======================================================
    #  Semantic search (soft threshold)
    # ======================================================
    def search(self, query, top_k=8):
        if self.index.ntotal == 0:
            return []

        query_vec = self.embedder.encode(
            [query],
            normalize_embeddings=True
        ).astype("float32")

        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.text_chunks) and score >= self.similarity_threshold:
                results.append(self.text_chunks[idx])

        return results

    # ======================================================
    #  SMART SEARCH (semantic + lexical fallback)
    # ======================================================
    def smart_search(self, query, top_k=12):
        """
        Hybrid retrieval:
        - semantic FAISS search
        - lexical fallback for headings/titles
        """

        semantic_hits = self.search(query, top_k=top_k)

        # --- lexical fallback (VERY IMPORTANT) ---
        words = set(query.lower().split())
        lexical_hits = [
            chunk for chunk in self.text_chunks
            if any(w in chunk.lower() for w in words)
        ]

        
        combined = []
        seen = set()

        for c in semantic_hits + lexical_hits:
            if c not in seen:
                combined.append(c)
                seen.add(c)

        return combined[:top_k]

    
    def _split_text(self, text, chunk_size=800, overlap=120):
        words = text.split()
        chunks = []

        i = 0
        while i < len(words):
            chunk = words[i:i + chunk_size]
            chunks.append(" ".join(chunk))
            i += chunk_size - overlap

        return chunks
