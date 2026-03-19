"""
benchmark.py - RAG Accuracy and Latency Benchmarking Tool
Run from project root: python benchmark.py
"""

import time
import json
import os
import re
from datetime import datetime

# ── Setup ─────────────────────────────────────────────────────────────────────

RESULTS_FILE = "data/benchmark_results.json"
os.makedirs("data", exist_ok=True)


# ── Color output for terminal ─────────────────────────────────────────────────

def green(t):  return f"\033[92m{t}\033[0m"
def red(t):    return f"\033[91m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def bold(t):   return f"\033[1m{t}\033[0m"
def cyan(t):   return f"\033[96m{t}\033[0m"


# ── 1. LATENCY BENCHMARK ──────────────────────────────────────────────────────

def benchmark_latency(runs: int = 3):
    print(bold("\n" + "="*60))
    print(bold("  LATENCY BENCHMARK: Local (Llama3) vs API (Gemini)"))
    print(bold("="*60))

    test_prompts = [
        "What is the capital of France?",
        "Explain what machine learning is in one sentence.",
        "What is 15 multiplied by 27?",
    ]

    local_times = []
    api_times   = []

    try:
        from models.local_llm import local_generate
        LOCAL_OK = True
    except Exception as e:
        print(red(f"Local model not available: {e}"))
        LOCAL_OK = False

    try:
        from models.gemini_llm import gemini_generate
        API_OK = True
    except Exception as e:
        print(red(f"API model not available: {e}"))
        API_OK = False

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{cyan(f'Test {i}/{len(test_prompts)}')} : {prompt}")
        print("-" * 50)

        # Local model
        if LOCAL_OK:
            times = []
            for run in range(runs):
                start    = time.time()
                response = local_generate(prompt)
                elapsed  = time.time() - start
                times.append(elapsed)
                print(f"  Local  run {run+1}: {elapsed:.2f}s  |  {response[:60]}...")

            avg_local = sum(times) / len(times)
            local_times.append(avg_local)
            print(f"  {yellow(f'Local avg: {avg_local:.2f}s')}")

        # API model — only 1 run per prompt to avoid free tier rate limit
        if API_OK:
            times = []
            print(f"  Waiting 15s for API rate limit...")
            time.sleep(15)
            start    = time.time()
            response = gemini_generate(prompt)
            elapsed  = time.time() - start
            times.append(elapsed)
            print(f"  API    run 1: {elapsed:.2f}s  |  {response[:60]}...")

            avg_api = elapsed
            api_times.append(avg_api)
            print(f"  {yellow(f'API avg: {avg_api:.2f}s')}")

    # Summary
    print(bold("\n" + "="*60))
    print(bold("  LATENCY SUMMARY"))
    print("="*60)

    if local_times and api_times:
        overall_local = sum(local_times) / len(local_times)
        overall_api   = sum(api_times)   / len(api_times)
        faster        = "Local" if overall_local < overall_api else "API"
        diff          = abs(overall_local - overall_api)

        print(f"  Local (Llama3) average : {overall_local:.2f}s")
        print(f"  API   (Gemini) average : {overall_api:.2f}s")
        print(f"  {green(faster)} is faster by {diff:.2f}s")

        return {
            "local_avg_seconds": round(overall_local, 3),
            "api_avg_seconds":   round(overall_api, 3),
            "faster":            faster,
            "difference_seconds": round(diff, 3),
        }
    return {}


# ── 2. RAG ACCURACY BENCHMARK ─────────────────────────────────────────────────

def keyword_search(chunks: list[str], query: str, top_k: int = 5) -> list[str]:
    """Basic keyword search — splits query, counts word matches per chunk."""
    stopwords = {
        "what", "is", "the", "a", "an", "of", "in", "to",
        "and", "or", "how", "who", "when", "where", "are",
    }
    words = [w for w in query.lower().split() if w not in stopwords]

    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for w in words if w in chunk_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def contains_answer(chunks: list[str], expected_keywords: list[str]) -> bool:
    """Check if any chunk contains the expected answer keywords."""
    combined = " ".join(chunks).lower()
    return all(kw.lower() in combined for kw in expected_keywords)


def benchmark_rag(pdf_path: str = None):
    print(bold("\n" + "="*60))
    print(bold("  RAG ACCURACY BENCHMARK: FAISS vs Keyword Search"))
    print(bold("="*60))

    from rag.vector_store import PDFVectorStore

    store = PDFVectorStore()

    # Load PDF if specified and not already loaded
    if pdf_path:
        filename = os.path.basename(pdf_path)
        if filename not in store.loaded_files:
            print(f"\nLoading PDF: {filename}")
            try:
                count = store.load_pdf(filename)
                print(f"Loaded {count} chunks.")
            except Exception as e:
                print(red(f"Could not load PDF: {e}"))
                return {}
    elif not store.text_chunks:
        print(red("No PDF loaded. Either:"))
        print("  1. Run the bot first and upload a PDF")
        print("  2. Pass a pdf_path to this function")
        print(red("Skipping RAG benchmark."))
        return {}

    print(f"\nUsing {len(store.text_chunks)} chunks from: {list(store.loaded_files)}")

    # Generate test queries from actual chunk content
    # Pick 5 random chunks and use their first sentence as the query
    import random
    random.seed(42)
    sample_chunks = random.sample(store.text_chunks, min(5, len(store.text_chunks)))

    test_cases = []
    for chunk in sample_chunks:
        # Use first sentence as query, first 3 meaningful words as expected answer
        sentences = chunk.split(".")
        if not sentences:
            continue
        query    = sentences[0].strip()[:100]
        keywords = [w for w in chunk.split() if len(w) > 4][:3]
        if query and keywords:
            test_cases.append({"query": query, "expected_keywords": keywords})

    if not test_cases:
        print(red("Could not generate test cases from PDF content."))
        return {}

    faiss_hits   = 0
    keyword_hits = 0
    results      = []

    print(f"\nRunning {len(test_cases)} test queries...\n")
    print("-" * 60)

    for i, tc in enumerate(test_cases, 1):
        query    = tc["query"]
        expected = tc["expected_keywords"]

        print(f"{cyan(f'Query {i}:')} {query[:70]}...")
        print(f"  Expected keywords: {expected}")

        # FAISS semantic search
        t0          = time.time()
        faiss_res   = store.search(query, top_k=5)
        faiss_time  = time.time() - t0
        faiss_found = contains_answer(faiss_res, expected)

        # Keyword search
        t0           = time.time()
        kw_res       = keyword_search(store.text_chunks, query, top_k=5)
        kw_time      = time.time() - t0
        kw_found     = contains_answer(kw_res, expected)

        if faiss_found: faiss_hits += 1
        if kw_found:    keyword_hits += 1

        faiss_status   = green("FOUND") if faiss_found else red("MISSED")
        keyword_status = green("FOUND") if kw_found   else red("MISSED")

        print(f"  FAISS   : {faiss_status}   ({faiss_time*1000:.1f}ms)")
        print(f"  Keyword : {keyword_status} ({kw_time*1000:.1f}ms)")
        print()

        results.append({
            "query":         query,
            "faiss_found":   faiss_found,
            "keyword_found": kw_found,
            "faiss_ms":      round(faiss_time * 1000, 2),
            "keyword_ms":    round(kw_time * 1000, 2),
        })

    total         = len(test_cases)
    faiss_acc     = faiss_hits   / total * 100
    keyword_acc   = keyword_hits / total * 100

    print(bold("="*60))
    print(bold("  RAG ACCURACY SUMMARY"))
    print("="*60)
    print(f"  FAISS semantic search : {faiss_hits}/{total} = {green(f'{faiss_acc:.0f}%')}")
    print(f"  Keyword search        : {keyword_hits}/{total} = {yellow(f'{keyword_acc:.0f}%')}")

    if faiss_acc > keyword_acc:
        print(f"\n  {green('FAISS wins')} by {faiss_acc - keyword_acc:.0f} percentage points")
    elif keyword_acc > faiss_acc:
        print(f"\n  {yellow('Keyword wins')} by {keyword_acc - faiss_acc:.0f} percentage points")
    else:
        print(f"\n  Both methods tied at {faiss_acc:.0f}%")

    return {
        "faiss_accuracy_pct":   round(faiss_acc, 1),
        "keyword_accuracy_pct": round(keyword_acc, 1),
        "faiss_hits":           faiss_hits,
        "keyword_hits":         keyword_hits,
        "total_queries":        total,
        "details":              results,
    }


# ── 3. SAVE RESULTS ───────────────────────────────────────────────────────────

def save_results(latency: dict, rag: dict):
    existing = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                existing = json.load(f)
        except Exception:
            pass

    entry = {
        "timestamp": datetime.now().isoformat(),
        "latency":   latency,
        "rag":       rag,
    }
    existing.append(entry)

    with open(RESULTS_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"\n{green('Results saved to:')} {RESULTS_FILE}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrix AI Benchmark Tool")
    parser.add_argument("--latency",  action="store_true", help="Run latency benchmark only")
    parser.add_argument("--rag",      action="store_true", help="Run RAG accuracy benchmark only")
    parser.add_argument("--pdf",      type=str, default=None, help="PDF filename to use for RAG test (must be in pdfs/ folder)")
    parser.add_argument("--runs",     type=int, default=3,    help="Number of runs per latency test (default 3)")
    args = parser.parse_args()

    run_all = not args.latency and not args.rag

    latency_results = {}
    rag_results     = {}

    if args.latency or run_all:
        latency_results = benchmark_latency(runs=args.runs)

    if args.rag or run_all:
        pdf_path = os.path.join("pdfs", args.pdf) if args.pdf else None
        rag_results = benchmark_rag(pdf_path=pdf_path)

    if latency_results or rag_results:
        save_results(latency_results, rag_results)

    print(bold("\nBenchmark complete.\n"))