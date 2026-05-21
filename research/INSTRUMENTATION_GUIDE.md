"""
Instrumentation for Orchestrix research: Add this to core/orchestrator.py

This code tracks the 4-stage routing pipeline for research experiments.
Add these imports, functions, and integrate into generate_response().
"""

# ============================================================================
# STEP 1: Add these imports at the top of core/orchestrator.py
# ============================================================================

import uuid
import time
import json
from pathlib import Path


# ============================================================================
# STEP 2: Add these functions in core/orchestrator.py (after imports)
# ============================================================================

# Ensure logs directory exists
LOGS_DIR = Path("research/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
TRACE_FILE = LOGS_DIR / "orchestration_trace.jsonl"

def log_orchestration_event(event: dict) -> None:
    """Log orchestration trace event to JSONL file for research analysis."""
    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"Warning: Failed to log orchestration event: {e}")


# ============================================================================
# STEP 3: Modify generate_response() function like this:
# ============================================================================

# BEFORE: async def generate_response(user_input: str, model_type: str = "local") -> str:
# AFTER (add instrumentation):

async def generate_response(user_input: str, model_type: str = "local") -> str:
    """
    Process user input through 4-stage orchestration pipeline.
    INSTRUMENTED for research experiments.
    """
    
    # -------- START INSTRUMENTATION --------
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    trace = {
        "request_id": request_id,
        "timestamp": start_time,
        "input": user_input[:100],  # First 100 chars only
        "stage_reached": None,
        "stages_executed": [],
        "total_latency_ms": 0,
        "confidence": None,
        "model_type": model_type,
    }
    # -------- END INSTRUMENTATION SETUP --------
    
    try:
        # ========== STAGE 1: Pattern Matching ==========
        stage_start = time.time()
        
        # Check for simple patterns (tasks, weather, etc.)
        from tools.feature_intent import detect_task_intent
        
        task_result = detect_task_intent(user_input)
        if task_result['intent'] != 'none':
            # Pattern matched! Stage 1 handled it
            trace["stage_reached"] = 1
            trace["stages_executed"].append(1)
            trace["confidence"] = task_result.get('confidence', 0.8)
            
            # Log before returning
            trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
            log_orchestration_event(trace)
            
            return task_result['response']
        
        # ========== STAGE 2: LLM Intent Detection ==========
        stage_start = time.time()
        
        from models.local_llm import LocalLLM
        
        llm = LocalLLM(model_type)
        intent = llm.detect_intent(user_input)
        confidence = intent.get('confidence', 0.5)
        
        trace["stages_executed"].append(2)
        
        if confidence > 0.6:
            # LLM confident - route to handler
            trace["stage_reached"] = 2
            trace["confidence"] = confidence
            
            # ========== STAGE 3: Specialized Handlers ==========
            stage_start = time.time()
            
            handler_response = route_to_handler(intent, user_input)
            if handler_response:
                trace["stage_reached"] = 3
                trace["stages_executed"].append(3)
                
                # Log before returning
                trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
                log_orchestration_event(trace)
                
                return handler_response
        
        # ========== STAGE 4: Fallback Reasoning ==========
        stage_start = time.time()
        
        trace["stage_reached"] = 4
        trace["stages_executed"].append(4)
        trace["confidence"] = 0.3  # Low confidence - fallback
        
        fallback_response = llm.generate_response(user_input)
        
        # Log before returning
        trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
        log_orchestration_event(trace)
        
        return fallback_response
    
    except Exception as e:
        # Error case - still log
        trace["error"] = str(e)
        trace["stage_reached"] = -1  # Error state
        trace["total_latency_ms"] = int((time.time() - start_time) * 1000)
        log_orchestration_event(trace)
        raise


# ============================================================================
# STEP 4: Add this helper function for routing
# ============================================================================

def route_to_handler(intent: dict, user_input: str) -> str:
    """Route to specialized handler based on detected intent."""
    from tools.google_tasks_tool import handle_task_command
    from tools.weather_tool import get_weather
    from tools.web_search import search_web
    
    intent_type = intent.get('type')
    
    if intent_type == 'task':
        return handle_task_command(user_input)
    elif intent_type == 'weather':
        return get_weather()
    elif intent_type == 'web_search':
        query = intent.get('query', user_input)
        return search_web(query)
    
    return None


# ============================================================================
# STEP 5: Integration Checklist
# ============================================================================
#
# After adding this code, verify:
#
# [ ] Step 1: Imports added (uuid, time, json, Path)
# [ ] Step 2: log_orchestration_event() function added
# [ ] Step 2: LOGS_DIR and TRACE_FILE paths defined
# [ ] Step 3: generate_response() instrumented with trace tracking
# [ ] Step 3: All 4 stages record stage_reached before returning
# [ ] Step 4: route_to_handler() function added
# [ ] Step 5: Test run to generate first trace:
#        python main.py  # Type: "show my tasks"
#        ls research/logs/orchestration_trace.jsonl  # Should exist
#
# Then collect 500 queries:
#        python research/generate_test_queries.py
#        python research/run_all_experiments.sh
#
