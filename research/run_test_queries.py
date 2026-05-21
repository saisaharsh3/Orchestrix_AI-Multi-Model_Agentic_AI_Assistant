#!/usr/bin/env python3
"""
Run all test queries through orchestrator to collect traces.
This script simulates user inputs and collects performance data.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import generate_response

def run_test_queries(limit=None, verbose=False):
    """Run test queries and collect traces."""
    
    query_file = Path("research/test_queries.json")
    if not query_file.exists():
        print("❌ test_queries.json not found. Run generate_test_queries.py first.")
        return
    
    with open(query_file) as f:
        queries = json.load(f)
    
    if limit:
        queries = queries[:limit]
    
    print(f"Running {len(queries)} test queries through orchestrator...")
    print("=" * 70)
    
    success = 0
    errors = 0
    
    for idx, query_obj in enumerate(queries, 1):
        query = query_obj["query"]
        category = query_obj["category"]
        
        try:
            # Run through orchestrator (this will generate trace)
            response = generate_response(
                user_input=query,
                model_type="local",  # Use local model for faster execution
                use_web=False,  # Disable web search for deterministic results
                use_pdf=False,
                user_id=f"test_user_{category}"
            )
            
            success += 1
            
            # Progress indicator
            if verbose or idx % 20 == 0:
                print(f"[{idx:3d}/{len(queries)}] OK {category:10s} | {query[:50]:50s}")
        
        except Exception as e:
            errors += 1
            print(f"[{idx:3d}/{len(queries)}] ER {category:10s} | ERROR: {str(e)[:40]}")
    
    print("=" * 70)
    print(f"\nQuery Execution Summary:")
    print(f"   Total:     {len(queries)}")
    print(f"   Success:   {success}")
    print(f"   Errors:    {errors}")
    print(f"   Success Rate: {(success/len(queries)*100):.1f}%")
    
    # Verify trace file
    trace_file = Path("research/logs/orchestration_trace.jsonl")
    if trace_file.exists():
        with open(trace_file) as f:
            trace_lines = f.readlines()
        print(f"\nTrace Statistics:")
        print(f"   Trace entries: {len(trace_lines)}")
        print(f"   Trace file: {trace_file}")
    
    return success == len(queries)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run test queries and collect traces")
    parser.add_argument("--limit", type=int, help="Limit number of queries to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    success = run_test_queries(limit=args.limit, verbose=args.verbose)
    sys.exit(0 if success else 1)
