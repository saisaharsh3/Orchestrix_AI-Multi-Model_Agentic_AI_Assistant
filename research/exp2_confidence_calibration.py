#!/usr/bin/env python3
"""
Experiment 2: Confidence Calibration Analyzer
Analyzes confidence score distributions and calibration quality.
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics

def expected_calibration_error(confidences, accuracies, n_bins=4):
    """Calculate Expected Calibration Error (ECE)."""
    if not confidences:
        return 0.0
    
    # Bin confidences and compute ECE
    bin_width = 1.0 / n_bins
    ece = 0.0
    
    for bin_idx in range(n_bins):
        bin_lower = bin_idx * bin_width
        bin_upper = (bin_idx + 1) * bin_width
        
        # Get confidences and accuracies in this bin
        in_bin = [
            (conf, acc) for conf, acc in zip(confidences, accuracies)
            if bin_lower <= conf < bin_upper
        ]
        
        if not in_bin:
            continue
        
        bin_confidence = statistics.mean([conf for conf, _ in in_bin])
        bin_accuracy = statistics.mean([acc for _, acc in in_bin])
        bin_size = len(in_bin)
        
        ece += (bin_size / len(confidences)) * abs(bin_confidence - bin_accuracy)
    
    return ece

LABELS_FILE = "research/calibration_labels.json"


def _load_human_labels(path=LABELS_FILE):
    """
    Ground-truth labels as [(confidence, 1.0 | 0.0)].

    File format: {"labels": [{"model_confidence": 0.8, "human_label": "correct" | "incorrect",
                              "auto_label": false}, ...]}
    Entries with auto_label=true are ignored: they are not ground truth.
    """
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        labels = json.load(f).get("labels", [])
    return [
        (float(item["model_confidence"]), 1.0 if item["human_label"] == "correct" else 0.0)
        for item in labels
        if not item.get("auto_label") and item.get("human_label") in {"correct", "incorrect"}
    ]


def analyze_confidence_calibration(trace_file="research/logs/orchestration_trace.jsonl"):
    """Analyze confidence score distributions."""
    
    if not Path(trace_file).exists():
        print(f"Error: Trace file not found: {trace_file}")
        print("Run experiments first to generate traces.")
        return
    
    # Read all trace events
    traces = []
    with open(trace_file, "r") as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
    
    if not traces:
        print("No trace data found.")
        return
    
    # Extract confidence scores
    confidences = [trace.get("confidence", 0.5) for trace in traces if "confidence" in trace]
    
    if not confidences:
        print("No confidence scores found in traces.")
        return
    
    print("\n" + "="*60)
    print("EXPERIMENT 2: CONFIDENCE CALIBRATION")
    print("="*60)
    
    # Confidence distribution analysis
    print("\nConfidence Score Distribution:")
    print("-" * 60)
    
    # Bin confidences
    bins = [(0.0, 0.3), (0.3, 0.6), (0.6, 0.8), (0.8, 1.0)]
    bin_counts = defaultdict(int)
    
    for conf in confidences:
        for bin_range in bins:
            if bin_range[0] <= conf <= bin_range[1]:
                bin_counts[bin_range] += 1
                break
    
    for bin_range in bins:
        count = bin_counts[bin_range]
        percentage = (count / len(confidences)) * 100
        bar = "█" * int(percentage / 2)
        print(f"[{bin_range[0]:.1f}-{bin_range[1]:.1f}]  {count:>4} requests ({percentage:>5.1f}%) {bar}")
    
    # Statistical summary
    print("\nStatistical Summary:")
    print("-" * 60)
    print(f"Total scores:        {len(confidences)}")
    print(f"Mean:                {statistics.mean(confidences):.3f}")
    print(f"Median:              {statistics.median(confidences):.3f}")
    print(f"Std Dev:             {statistics.stdev(confidences):.3f}")
    print(f"Min:                 {min(confidences):.3f}")
    print(f"Max:                 {max(confidences):.3f}")
    print(f"Q1 (25th percentile):{statistics.quantiles(confidences, n=4)[0]:.3f}")
    print(f"Q3 (75th percentile):{statistics.quantiles(confidences, n=4)[2]:.3f}")
    
    # ECE needs ground truth: was each answer actually correct?
    # Only human-made labels count (auto-generated labels are skipped).
    labelled = _load_human_labels()
    print("\nCalibration Metrics:")
    print("-" * 60)
    if len(labelled) >= 30:
        ece = expected_calibration_error([c for c, _ in labelled], [a for _, a in labelled])
        print(f"Expected Calibration Error (ECE): {ece:.4f}  (n={len(labelled)} human labels)")
        print("  (Lower is better; <0.05 is well-calibrated)")
    else:
        ece = None
        print(f"ECE not computed: {len(labelled)} human labels found, need at least 30.")
        print(f"  Add labels to {LABELS_FILE} (see _load_human_labels for the format).")
    
    # Threshold analysis
    print("\nThreshold Analysis (proposed decision points):")
    print("-" * 60)
    thresholds = [0.3, 0.6, 0.9]
    for threshold in thresholds:
        above = sum(1 for c in confidences if c >= threshold)
        percentage = (above / len(confidences)) * 100
        print(f"Confidence >= {threshold}: {above:>4} requests ({percentage:>5.1f}%)")
    
    # Save results
    results = {
        "total_scores": len(confidences),
        "mean_confidence": statistics.mean(confidences),
        "median_confidence": statistics.median(confidences),
        "std_dev": statistics.stdev(confidences),
        "ece": ece,
        "distribution": {
            "very_low_0_0_0_3": bin_counts[(0.0, 0.3)],
            "low_0_3_0_6": bin_counts[(0.3, 0.6)],
            "high_0_6_0_8": bin_counts[(0.6, 0.8)],
            "very_high_0_8_1_0": bin_counts[(0.8, 1.0)]
        },
        "key_findings": {
            "average_confidence": round(statistics.mean(confidences), 3),
            "well_calibrated": None if ece is None else ece < 0.05,
            "human_labels": len(labelled),
        }
    }
    
    output_file = Path("research/results_exp2.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    print("\n⚠  NOTE: For proper ECE calculation, manually label 100 random queries")
    print("        with ground-truth correctness, then run calibration curve analysis.")
    print("="*60 + "\n")

if __name__ == "__main__":
    analyze_confidence_calibration()
