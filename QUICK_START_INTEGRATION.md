"""
QUICK START: Using New Systems
"""

# ============================================================================
# 1. LOGGING SYSTEM - Replace all print() with logger
# ============================================================================

# BEFORE:
# print(f"Error: {e}")
# print("Operation successful")

# AFTER:
from core.logger import get_logger

logger = get_logger(__name__)

logger.info("Operation started", extra={"user_id": user_id})
logger.debug(f"Maps search for: {query}")
logger.warning(f"API call delayed: {wait_time}s")
logger.error(f"Operation failed", exc_info=True)

# ============================================================================
# 2. RATE LIMITING - Prevent API overload
# ============================================================================

from core.rate_limiter import with_rate_limit, with_retry, gemini_limiter
from core.model_manager import generate_llm

# Add decorators to functions
@with_rate_limit("gemini", gemini_limiter)
@with_retry(max_attempts=3, backoff_factor=1.5)
def call_gemini(prompt: str) -> str:
    """Call Gemini API with automatic rate limiting and retry"""
    return generate_llm(prompt, "api")

# Usage:
# response = call_gemini("What is the capital of India?")
# Automatically handles:
# - Rate limiting (max 60 calls/min)
# - Retries with exponential backoff on failure
# - Logging of attempts and failures

# ============================================================================
# 3. USER PREFERENCES - Multi-user support
# ============================================================================

from config.settings import settings, UserPreferences

# Get user's preferred model
user_prefs = UserPreferences.get_user_prefs(user_id)
model = user_prefs["preferred_model"]  # "api" or "local"
tone = user_prefs["default_tone"]      # "casual", "formal", etc.

# Update user's preference
UserPreferences.set_user_pref(user_id, "default_tone", "casual")
UserPreferences.set_user_pref(user_id, "location", {"lat": 17.4, "lon": 78.6})

# Access global settings
if settings.ENABLE_WEB_SEARCH:
    result = web_search(query)

# ============================================================================
# 4. INTEGRATION EXAMPLE - Update orchestrator.py
# ============================================================================

# Add this to the top of core/orchestrator.py:
from core.logger import get_logger
from core.rate_limiter import with_rate_limit, with_retry, gemini_limiter
from config.settings import settings, UserPreferences

logger = get_logger(__name__)

# Update generate_response function signature:
def generate_response(
    user_input: str,
    model_type: str = "api",
    pdf_store=None,
    use_web: bool = True,
    use_pdf: bool = False,
    user_id: str = None,
) -> str:
    
    # Start logging
    logger.info(f"Processing request", extra={
        "user_id": user_id,
        "input_length": len(user_input),
        "model": model_type
    })
    
    # Load user preferences
    if user_id:
        user_prefs = UserPreferences.get_user_prefs(user_id)
        model_type = user_prefs.get("preferred_model", model_type)
        logger.debug(f"Using user preference: model={model_type}")
    
    try:
        # ... existing code ...
        
        # Replace direct generate_llm calls with rate-limited version
        @with_rate_limit("gemini", gemini_limiter)
        @with_retry(max_attempts=2)
        def safe_llm_call(prompt, model):
            return generate_llm(prompt, model)
        
        response = safe_llm_call(prompt, model_type)
        
        logger.info(f"Response generated", extra={
            "user_id": user_id,
            "response_length": len(response)
        })
        
        return response
    
    except Exception as e:
        logger.error(f"Response generation failed", exc_info=True)
        return f" Error: {str(e)}"

# ============================================================================
# 5. ENVIRONMENT SETUP - Create .env file
# ============================================================================

# Create .env in project root:
"""
# API Keys
GEMINI_API_KEY=your_api_key_here
TELEGRAM_TOKEN=your_token_here

# Model settings
DEFAULT_MODEL=local
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=neural-chat

# Feature toggles
ENABLE_WEB_SEARCH=true
ENABLE_VOICE=true
ENABLE_PDF_RAG=true
ENABLE_PHONE_ADB=true

# Rate limiting
GEMINI_RATE_LIMIT=60
WEB_SEARCH_RATE_LIMIT=30

# Logging
LOG_LEVEL=INFO
ENABLE_DEBUG=false
"""

# ============================================================================
# 6. TO ENABLE ALL THREE SYSTEMS:
# ============================================================================

# Step 1: Create .env file (see above)
# Step 2: Add imports to core/orchestrator.py (see example above)
# Step 3: Replace print() calls with logger.info/error/debug/warning
# Step 4: Add @with_rate_limit and @with_retry decorators to API calls
# Step 5: Use UserPreferences in handlers for personalization

# Then test:
# python telegram_bot.py
# → Should see logs in console and logs/ directory
# → Should handle rate limiting gracefully
# → User preferences auto-created on first use

# ============================================================================
# 7. CHECK LOGS
# ============================================================================

# Logs are saved to:
# - logs/orchestrix_20260320.log (all operations)
# - logs/errors_20260320.log (errors only)
# - console (INFO level and above)

# Example log output:
# 2026-03-20 14:23:45 | root | INFO | Processing request
# 2026-03-20 14:23:45 | core.orchestrator | DEBUG | Using user preference: model=api
# 2026-03-20 14:23:46 | core.rate_limiter | INFO | Attempt 1/3 for safe_llm_call
# 2026-03-20 14:23:47 | root | INFO | Response generated
