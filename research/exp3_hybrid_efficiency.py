#!/usr/bin/env python3
"""
Experiment 3: Hybrid Model Efficiency.

Compares measured end-to-end latency of the local model (Ollama) and the API
model (Gemini) per query category, using the orchestration trace.

Collect data first:
    python research/run_test_queries.py --model both

Each trace's category is found by matching its input text to
research/test_queries.json. Nothing is estimated or filled in: categories
with no data for a model are reported as missing.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

TRACE_FILE = "research/logs/orchestration_trace.jsonl"
QUERY_FILE = "research/test_queries.json"
OUTPUT_FILE = "research/results_exp3.json"
FALLBACK_STAGE = 4  # only LLM-answered requests compare the models fairly


def _p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def _summary(values):
    if not values:
        return None
    return {
        "n": len(values),
        "median_ms": statistics.median(values),
        "mean_ms": round(statistics.mean(values), 1),
        "p95_ms": _p95(values),
    }


def analyze_hybrid_efficiency(trace_file=TRACE_FILE, query_file=QUERY_FILE):
    if not Path(trace_file).exists() or not Path(query_file).exists():
        print(f"Required files not found:\n  {trace_file}\n  {query_file}")
        print("Run: python research/run_test_queries.py --model both")
        return None

    with open(query_file, encoding="utf-8") as f:
        categories = {q["query"][:100]: q["category"] for q in json.load(f)}

    latencies = defaultdict(lambda: defaultdict(list))  # model -> category -> [ms]
    unmatched = 0
    with open(trace_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            trace = json.loads(line)
            if trace.get("stage_reached") != FALLBACK_STAGE:
                continue
            category = categories.get(trace.get("input", ""))
            if category is None:
                unmatched += 1
                continue
            latencies[trace.get("model_type", "unknown")][category].append(trace.get("total_latency_ms", 0))

    print("\n" + "=" * 72)
    print("EXPERIMENT 3: HYBRID MODEL EFFICIENCY (measured, stage-4 requests)")
    print("=" * 72)
    print(f"{'Category':<10} {'Local median':>14} {'API median':>12} {'n local':>9} {'n api':>7}  Faster")
    print("-" * 72)

    results = {}
    for category in ["simple", "complex", "rag"]:
        local = _summary(latencies["local"][category])
        api = _summary(latencies["api"][category])
        results[category] = {"local": local, "api": api}
        if local and api:
            faster = "local" if local["median_ms"] < api["median_ms"] else "api"
            ratio = max(local["median_ms"], api["median_ms"]) / max(1, min(local["median_ms"], api["median_ms"]))
            results[category]["faster"] = faster
            results[category]["median_ratio"] = round(ratio, 2)
            print(f"{category:<10} {local['median_ms']:>11.0f} ms {api['median_ms']:>9.0f} ms "
                  f"{local['n']:>9} {api['n']:>7}  {faster} ({ratio:.2f}x)")
        else:
            missing = ", ".join(m for m, s in (("local", local), ("api", api)) if not s)
            print(f"{category:<10} {'—':>14} {'—':>12} {'':>9} {'':>7}  no data for: {missing}")

    if unmatched:
        print(f"\n{unmatched} stage-4 traces did not match a test query and were ignored.")
    print("\nAccuracy is not measured here; it needs labelled answers (see Experiment 2).")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"latency_by_category": results, "unmatched_traces": unmatched}, f, indent=2)
    print(f"\nResults saved to: {OUTPUT_FILE}\n")
    return results


if __name__ == "__main__":
    analyze_hybrid_efficiency()
