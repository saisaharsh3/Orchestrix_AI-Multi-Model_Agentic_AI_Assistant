"""
core/rate_limiter.py - API Rate Limiting & Retry Strategy
Prevents hitting API limits and provides graceful degradation
"""

import time
from functools import wraps
from typing import Callable, Any
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Track API calls and enforce rate limits"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = {}
    
    def wait_if_needed(self, service: str):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        if service in self.last_call_time:
            elapsed = now - self.last_call_time[service]
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.info(f"Rate limit: waiting {wait_time:.2f}s for {service}")
                time.sleep(wait_time)
        
        self.last_call_time[service] = time.time()
    
    def reset(self, service: str = None):
        """Reset rate limit counter"""
        if service:
            self.last_call_time.pop(service, None)
        else:
            self.last_call_time.clear()


# Global rate limiter instances
gemini_limiter = RateLimiter(calls_per_minute=60)  # Google Gemini
web_limiter = RateLimiter(calls_per_minute=30)     # Web search
maps_limiter = RateLimiter(calls_per_minute=50)    # Maps API
news_limiter = RateLimiter(calls_per_minute=30)    # News search


def with_rate_limit(service: str, limiter: RateLimiter):
    """Decorator to add rate limiting to any function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter.wait_if_needed(service)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Decorator to add exponential backoff retry logic
    
    Usage:
        @with_retry(max_attempts=3, backoff_factor=2.0)
        def call_api():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Attempt {attempt}/{max_attempts} for {func.__name__}")
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        wait_time = backoff_factor ** (attempt - 1)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}): {str(e)}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts",
                            exc_info=True
                        )
            
            raise last_exception or Exception(f"{func.__name__} failed")
        
        return wrapper
    return decorator


# Example usage:
# @with_rate_limit("gemini", gemini_limiter)
# @with_retry(max_attempts=3, backoff_factor=1.5)
# def generate_llm(prompt, model_type):
#     return api_call(prompt)
