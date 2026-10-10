# Orchestrix research

Five experiments on how the hybrid local/cloud assistant behaves. This page is
the single summary; the two long write-ups are
[exp4_privacy_model.md](exp4_privacy_model.md) and
[exp5_stylometry_analysis.md](exp5_stylometry_analysis.md).

> **Status of the numbers.** Earlier versions of these scripts filled gaps with
> placeholder values (Experiment 3 used fixed 45 ms / 380 ms latencies and
> Experiment 2 derived "accuracy" from confidence + 0.1). Those code paths have
> been removed. Results in [results/](results/) and any you generate now are
> measured. Re-run the pipeline below before quoting a figure.

## How requests are traced

Every request through `core/orchestrator.py` appends one JSON line to
`research/logs/orchestration_trace.jsonl` (disable with `ENABLE_RESEARCH_TRACE=false`):

| Field | Meaning |
|---|---|
| `stage_reached` | 0 command · 1 pattern handler · 2 Gemini tool routing · 3 retrieval (RAG / Wikipedia) · 4 LLM fallback |
| `total_latency_ms` | end-to-end time for the request |
| `model_type` | `local` (Ollama) or `api` (Gemini) |
| `confidence` | handler's confidence, when it reports one |
| `input` | first 100 characters of the message |

Stage definitions live in `core/handlers/base.py`.

## Running everything

```bash
pip install -r requirements-research.txt
python research/generate_test_queries.py          # writes research/test_queries.json
python research/run_test_queries.py --model both  # needs Ollama running and GEMINI_API_KEY
python research/exp1_orchestration_efficiency.py
python research/exp2_confidence_calibration.py
python research/exp3_hybrid_efficiency.py
python research/exp5_stylometry.py
python research/generate_graphs.py                # reads results_exp*.json, writes graphs/
```

`bash research/run_all_experiments.sh` runs the analysis steps in order.
Latency/RAG micro-benchmarks: `python scripts/benchmark.py` → [results/benchmark_results.json](results/benchmark_results.json).

## Experiments

### 1 · Orchestration efficiency
*How many requests are routed without asking an LLM what to do?*
Counts traces per stage. Stage 1 is the only LLM-free route; stage 3 still uses
an LLM to write the RAG answer.

**Measured so far** (recorded before every path was instrumented, so only
stages 1 and 4 appear):

| Run | Requests | Stage 1 (no LLM) | Stage 4 (LLM) |
|---|---|---|---|
| March 2026 (figure in the main README) | 39 | 12.8% | 87.2% |
| March–April 2026, full log | 210 | 8.1% | 91.9% (median 9.0 s vs 1.2 s) |

Re-run with the current tracing for a full distribution.

### 2 · Confidence calibration
*Do handler confidence scores match how often the answer is right?*
Reports the confidence distribution, and Expected Calibration Error **only**
when `research/calibration_labels.json` contains at least 30 human labels
(`auto_label: false`). Auto-generated labels are ignored.

**Status:** ECE not yet measured — no human labels exist.

### 3 · Hybrid efficiency
*Local vs cloud latency per query type (simple / complex / RAG).*
Uses stage-4 traces from `run_test_queries.py --model both`, matched to
`test_queries.json` by text. Missing data is reported as missing. Answer
accuracy is not measured here.

**Measured so far** ([results/benchmark_results.json](results/benchmark_results.json),
3 prompts × 3 runs, RTX 3050 Ti laptop): local llama3 8B q4 ≈ 1.1–1.2 s mean,
Gemini Flash ≈ 1.9–2.0 s mean. FAISS retrieval over one PDF: 6–19 ms per query
(5 queries). The per-category comparison needs an API run of the test set.

### 4 · Privacy threat model
Analytical, no code to run: [exp4_privacy_model.md](exp4_privacy_model.md).
Claim: in local mode, no PDF content (or any other request content) is sent to
an external API. Enforced in code:

- `core/model_manager.py` never switches local → cloud on its own; when the
  local model fails the user is told and must choose `/api` themselves.
- Email drafting, RAG and fallback answers all use the session's model.
- Gemini tool routing (stage 2) runs in API mode only.
- `tests/test_orchestrator.py` checks the first two.

Out of scope for the guarantee: web search queries (DuckDuckGo) and Wikipedia
lookups, which are sent to those services in both modes when enabled.

### 5 · Stylometric unlinkability
*Can someone holding both your cloud queries and your local queries tell they
were written by the same person?* Full write-up:
[exp5_stylometry_analysis.md](exp5_stylometry_analysis.md).

Measured on the synthetic queries in `test_queries.json` (12 style features,
cosine similarity):

| Defence | Mean max similarity | High-confidence links |
|---|---|---|
| None | 0.846 | 16 / 20 |
| Paraphrasing | 0.847 (no gain) | — |
| Random obfuscation | 0.814 (−3.7%) | — |
| **Style normalisation** | **0.689 (−18.5%)** | 6 / 20 |

Style normalisation ships as **Stealth Mode** (`/stealth_mode on`,
`core/stylometric_defense.py`), applied to API-mode queries. It is a partial
defence; stronger options (LLM paraphrasing, text differential privacy,
query pooling) are listed in the write-up. Limitation: synthetic queries, not
real users.

## Files

| Path | What |
|---|---|
| `exp1…exp3_*.py`, `exp5_stylometry.py` | analysis scripts |
| `exp4_privacy_model.md`, `exp5_stylometry_analysis.md` | write-ups |
| `generate_test_queries.py`, `test_queries.json` | test set (285 queries: 110 simple, 100 complex, 75 RAG) |
| `run_test_queries.py` | replays the test set through the orchestrator |
| `generate_graphs.py` | figures from `results_exp*.json` |
| `results/` | curated measured results (committed) |
| `logs/`, `graphs/`, `results_exp*.json` | generated locally (git-ignored) |
