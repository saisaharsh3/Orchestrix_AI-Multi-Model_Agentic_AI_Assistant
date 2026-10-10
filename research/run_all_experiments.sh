#!/bin/bash
#
# Run the research analysis scripts in order.
#
# Collect data first (needs Ollama running and GEMINI_API_KEY):
#   python research/generate_test_queries.py
#   python research/run_test_queries.py --model both
#
# Usage (from the repository root):
#   bash research/run_all_experiments.sh

set -e

RESEARCH_DIR="research"
TRACE_FILE="$RESEARCH_DIR/logs/orchestration_trace.jsonl"

if [ ! -f "$TRACE_FILE" ]; then
    echo "Missing $TRACE_FILE"
    echo "Run: python research/run_test_queries.py --model both"
    exit 1
fi
if [ ! -f "$RESEARCH_DIR/test_queries.json" ]; then
    echo "Missing $RESEARCH_DIR/test_queries.json"
    echo "Run: python research/generate_test_queries.py"
    exit 1
fi

echo "[1/5] Experiment 1: orchestration efficiency"
python "$RESEARCH_DIR/exp1_orchestration_efficiency.py"

echo "[2/5] Experiment 2: confidence calibration"
python "$RESEARCH_DIR/exp2_confidence_calibration.py"

echo "[3/5] Experiment 3: hybrid efficiency"
python "$RESEARCH_DIR/exp3_hybrid_efficiency.py"

echo "[4/5] Experiment 5: stylometric unlinkability"
python "$RESEARCH_DIR/exp5_stylometry.py"

echo "[5/5] Summary (only values computed above; nothing is filled in)"
python - <<'PYTHON_SCRIPT'
import json
from pathlib import Path

research = Path("research")
results = {}
for name in ["exp1", "exp2", "exp3", "exp5"]:
    path = research / f"results_{name}.json"
    if path.exists():
        results[name] = json.loads(path.read_text(encoding="utf-8"))

summary = {
    "experiments_with_results": sorted(results),
    "exp1_total_requests": results.get("exp1", {}).get("total_requests"),
    "exp1_key_findings": results.get("exp1", {}).get("key_findings"),
    "exp2_mean_confidence": results.get("exp2", {}).get("mean_confidence"),
    "exp2_ece": results.get("exp2", {}).get("ece"),  # null until human labels exist
    "exp3_latency_by_category": results.get("exp3", {}).get("latency_by_category"),
}
out = research / "summary.json"
out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(f"Summary saved: {out}")
PYTHON_SCRIPT

echo "Done. Graphs: python research/generate_graphs.py (needs requirements-research.txt)"
