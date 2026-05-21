#!/usr/bin/env python3
"""Generate 500 diverse test queries for Orchestrix research experiments."""

import json
import random
from pathlib import Path

# Create research directory if it doesn't exist
Path("research").mkdir(exist_ok=True)

# Define query templates by category
SIMPLE_PATTERNS = [
    ("show my tasks", "task_view", 1, 0.9),
    ("list tasks", "task_view", 1, 0.9),
    ("my to-do list", "task_view", 1, 0.9),
    ("add task {task_name}", "task_add", 1, 0.85),
    ("create a task for {task_name}", "task_add", 1, 0.85),
    ("new task: {task_name}", "task_add", 1, 0.85),
    ("mark {task_id} as done", "task_complete", 1, 0.9),
    ("complete task {task_id}", "task_complete", 1, 0.9),
    ("delete {task_id}", "task_delete", 1, 0.9),
    ("remove task {task_id}", "task_delete", 1, 0.9),
    ("what's the weather", "weather", 1, 0.85),
    ("weather today", "weather", 1, 0.85),
    ("tell me the weather", "weather", 1, 0.85),
    ("current time", "time", 1, 0.8),
    ("what time is it", "time", 1, 0.8),
    ("search for {query}", "web_search", 1, 0.8),
    ("google {query}", "web_search", 1, 0.8),
    ("find information about {query}", "web_search", 1, 0.8),
    ("define {word}", "wiki_search", 1, 0.8),
    ("what is {word}", "wiki_search", 1, 0.8),
    ("latest news about {topic}", "news", 1, 0.75),
    ("news on {topic}", "news", 1, 0.75),
]

COMPLEX_PATTERNS = [
    ("show me my calendar for next week and highlight meetings with john", "calendar_complex", 2, 0.65),
    ("remind me to call mom next tuesday at 3pm and send her my calendar", "calendar_reminder_complex", 2, 0.6),
    ("find flights from new york to london next month under 500 dollars", "travel_search", 2, 0.55),
    ("compare three weather forecasts and suggest best day for hiking", "weather_analysis", 2, 0.5),
    ("search for machine learning papers from 2024 and summarize top 5", "research_summary", 2, 0.55),
    ("create a weekly schedule with tasks, meetings, and reminders", "schedule_planning", 2, 0.6),
    ("analyze my spending patterns and suggest budget adjustments", "finance_analysis", 2, 0.55),
    ("find restaurants in downtown and filter by cuisine and ratings", "restaurant_search", 2, 0.5),
    ("plan a road trip route between three cities with stops", "route_planning", 2, 0.5),
    ("compare job postings from multiple companies for similar roles", "job_comparison", 2, 0.55),
    ("help me choose between two apartments based on price and location", "decision_support", 2, 0.5),
    ("create a learning plan for python with resources and timeline", "learning_plan", 2, 0.55),
    ("find local events this weekend matching my interests", "event_discovery", 2, 0.5),
    ("analyze competitor pricing and market trends in my industry", "market_analysis", 2, 0.55),
    ("generate a workout plan based on my fitness level and goals", "fitness_planning", 2, 0.5),
    ("find and compare insurance plans for comprehensive coverage", "insurance_comparison", 2, 0.55),
    ("create a content calendar for social media for the next month", "content_planning", 2, 0.6),
    ("analyze email sentiment and suggest reply strategies", "email_analysis", 2, 0.5),
    ("find investment opportunities aligned with my risk profile", "investment_planning", 2, 0.55),
    ("plan a month-long trip with budget and itinerary", "trip_planning", 2, 0.5),
]

RAG_PATTERNS = [
    ("summarize the main points from my pdf document", "pdf_summary", 3, 0.75),
    ("extract all entity names from the research paper", "pdf_extract", 3, 0.7),
    ("find sections discussing methodology in my document", "pdf_search", 3, 0.75),
    ("compare claims in document1 and document2", "pdf_compare", 3, 0.65),
    ("what are the conclusions in the uploaded pdf", "pdf_qa", 3, 0.7),
    ("identify statistical findings in the research document", "pdf_analysis", 3, 0.65),
    ("translate key concepts from the foreign language document", "pdf_translation", 3, 0.6),
    ("extract table data from my pdf document", "pdf_table_extraction", 3, 0.6),
    ("find references and citations in the research paper", "pdf_references", 3, 0.65),
    ("create an outline from the document structure", "pdf_outline", 3, 0.7),
    ("fact-check claims in my document against external sources", "pdf_verification", 3, 0.55),
    ("identify trends or patterns across multiple documents", "pdf_trend_analysis", 3, 0.6),
    ("extract requirements from the technical specification", "pdf_requirements", 3, 0.7),
    ("summarize financial reports and highlight key metrics", "pdf_finance_summary", 3, 0.65),
    ("find all action items from the meeting notes pdf", "pdf_action_items", 3, 0.7),
]

def generate_test_queries():
    """Generate 500 test queries across three complexity levels."""
    queries = []
    query_id = 1
    
    # Generate simple queries (225)
    sample_simple = random.sample(SIMPLE_PATTERNS, min(len(SIMPLE_PATTERNS), 45))
    for pattern, expected_stage_name, expected_stage, expected_confidence in sample_simple:
        for i in range(5):  # 5 variations per pattern = 225 total
            query = pattern
            # Replace placeholders
            if "{task_name}" in query:
                query = query.replace("{task_name}", f"Task {random.randint(1, 100)}")
            if "{task_id}" in query:
                query = query.replace("{task_id}", f"task_{random.randint(1, 50)}")
            if "{query}" in query:
                query = query.replace("{query}", random.choice(["python", "machine learning", "web development", "cloud computing"]))
            if "{word}" in query:
                query = query.replace("{word}", random.choice(["algorithm", "neural network", "API", "database"]))
            if "{topic}" in query:
                query = query.replace("{topic}", random.choice(["AI", "technology", "science", "politics"]))
            
            queries.append({
                "id": query_id,
                "query": query,
                "category": "simple",
                "expected_stage": expected_stage,
                "expected_stage_name": expected_stage_name,
                "expected_confidence": expected_confidence,
                "split": "train"
            })
            query_id += 1
    
    # Generate complex queries (175)
    sample_complex = random.sample(COMPLEX_PATTERNS, min(len(COMPLEX_PATTERNS), 35))
    for pattern, expected_stage_name, expected_stage, expected_confidence in sample_complex:
        for i in range(5):  # 5 variations per pattern = 175 total
            query = pattern
            # Replace placeholders
            if "{task_name}" in query:
                query = query.replace("{task_name}", f"Task {random.randint(1, 100)}")
            if "{topic}" in query:
                query = query.replace("{topic}", random.choice(["AI", "technology", "science", "finance"]))
            if "{query}" in query:
                query = query.replace("{query}", random.choice(["machine learning", "data science", "cloud computing"]))
            
            queries.append({
                "id": query_id,
                "query": query,
                "category": "complex",
                "expected_stage": expected_stage,
                "expected_stage_name": expected_stage_name,
                "expected_confidence": expected_confidence,
                "split": "test"
            })
            query_id += 1
    
    # Generate RAG queries (100)
    sample_rag = random.sample(RAG_PATTERNS, min(len(RAG_PATTERNS), 20))
    for pattern, expected_stage_name, expected_stage, expected_confidence in sample_rag:
        for i in range(5):  # 5 variations per pattern = 100 total
            queries.append({
                "id": query_id,
                "query": pattern,
                "category": "rag",
                "expected_stage": expected_stage,
                "expected_stage_name": expected_stage_name,
                "expected_confidence": expected_confidence,
                "split": "test"
            })
            query_id += 1
    
    # Shuffle to mix categories
    random.shuffle(queries)
    
    # Write to file
    output_file = Path("research/test_queries.json")
    with open(output_file, "w") as f:
        json.dump(queries, f, indent=2)
    
    print(f"✓ Generated {len(queries)} test queries")
    print(f"  - Simple: {sum(1 for q in queries if q['category'] == 'simple')}")
    print(f"  - Complex: {sum(1 for q in queries if q['category'] == 'complex')}")
    print(f"  - RAG: {sum(1 for q in queries if q['category'] == 'rag')}")
    print(f"  - Saved to: {output_file}")

if __name__ == "__main__":
    generate_test_queries()
