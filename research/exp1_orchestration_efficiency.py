#!/usr/bin/env python3
"""
Experiment 1: Orchestration Efficiency Analyzer
Analyzes which stage of the 4-stage orchestration pipeline handles each request.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import statistics

def analyze_orchestration_efficiency(trace_file="research/logs/orchestration_trace.jsonl"):
    """Analyze orchestration stage distribution and latencies."""
    
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
    
    # Analyze stage distribution
    stage_counts = Counter()
    stage_latencies = defaultdict(list)
    
    for trace in traces:
        stage = trace.get("stage_reached", None)
        if stage:
            stage_counts[stage] += 1
            latency = trace.get("total_latency_ms", 0)
            stage_latencies[stage].append(latency)
    
    total = len(traces)
    
    # Calculate statistics
    print("\n" + "="*60)
    print("EXPERIMENT 1: ORCHESTRATION EFFICIENCY")
    print("="*60)
    
    print("\nStage Distribution (where requests are handled):")
    print("-" * 60)
    
    stage_names = {
        1: "Stage 1: Pattern Matching",
        2: "Stage 2: LLM Intent Detection",
        3: "Stage 3: Specialized Handlers",
        4: "Stage 4: Fallback Reasoning"
    }
    
    for stage in sorted(stage_counts.keys()):
        count = stage_counts[stage]
        percentage = (count / total) * 100
        avg_latency = statistics.mean(stage_latencies[stage])
        
        print(f"{stage_names[stage]:<40} {count:>4} ({percentage:>5.1f}%) | Avg latency: {avg_latency:>6.1f}ms")
    
    # Key finding: percentage of requests NOT requiring expensive LLM (stages 1 & 3)
    non_llm_stages = stage_counts.get(1, 0) + stage_counts.get(3, 0)
    non_llm_percentage = (non_llm_stages / total) * 100
    
    print("\n" + "-" * 60)
    print(f"KEY FINDING: Non-LLM handling (Stages 1+3): {non_llm_percentage:.1f}%")
    print(f"             LLM-dependent (Stages 2+4):    {100-non_llm_percentage:.1f}%")
    print("-" * 60)
    
    # Latency analysis
    print("\nLatency Analysis:")
    print("-" * 60)
    
    all_latencies = [trace.get("total_latency_ms", 0) for trace in traces]
    print(f"Mean latency:   {statistics.mean(all_latencies):>7.1f} ms")
    print(f"Median latency: {statistics.median(all_latencies):>7.1f} ms")
    print(f"Stdev latency:  {statistics.stdev(all_latencies):>7.1f} ms")
    print(f"Min latency:    {min(all_latencies):>7.1f} ms")
    print(f"Max latency:    {max(all_latencies):>7.1f} ms")
    
    print("\nLatency by Stage:")
    print("-" * 60)
    for stage in sorted(stage_latencies.keys()):
        latencies = stage_latencies[stage]
        print(f"{stage_names[stage]:<40} {statistics.mean(latencies):>7.1f} ms (avg)")
    
    # Save results
    results = {
        "total_requests": total,
        "stage_distribution": {
            stage: {
                "count": stage_counts.get(stage, 0),
                "percentage": (stage_counts.get(stage, 0) / total) * 100,
                "avg_latency_ms": statistics.mean(stage_latencies.get(stage, [0]))
            }
            for stage in [1, 2, 3, 4]
        },
        "key_findings": {
            "non_llm_handling_percentage": non_llm_percentage,
            "llm_dependent_percentage": 100 - non_llm_percentage
        }
    }
    
    output_file = Path("research/results_exp1.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    print("="*60 + "\n")

if __name__ == "__main__":
    analyze_orchestration_efficiency()
