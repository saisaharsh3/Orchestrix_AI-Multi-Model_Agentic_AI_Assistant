"""
core/rate_limiter.py - API rate limiting and retry with backoff.
"""

import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from config.settings import settings
from core.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Enforce a minimum interval between calls to a service (thread-safe)."""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = max(1, calls_per_minute)
        self.min_interval = 60.0 / self.calls_per_minute
        self.last_call_time: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait_if_needed(self, service: str) -> None:
        with self._lock:
            now = time.time()
            last = self.last_call_time.get(service)
            wait_time = 0.0
            if last is not None:
                wait_time = max(0.0, self.min_interval - (now - last))
            # Reserve the slot before sleeping so concurrent callers queue up.
            self.last_call_time[service] = now + wait_time
        if wait_time > 0:
            logger.info(f"Rate limit: waiting {wait_time:.2f}s for {service}")
            time.sleep(wait_time)

    def reset(self, service: str | None = None) -> None:
        with self._lock:
            if service:
                self.last_call_time.pop(service, None)
            else:
                self.last_call_time.clear()


web_limiter = RateLimiter(calls_per_minute=settings.WEB_SEARCH_RATE_LIMIT)
news_limiter = RateLimiter(calls_per_minute=settings.NEWS_RATE_LIMIT)
maps_limiter = RateLimiter(calls_per_minute=settings.MAPS_RATE_LIMIT)


def with_rate_limit(service: str, limiter: RateLimiter):
    """Decorator: wait for the limiter before every call."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter.wait_if_needed(service)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    give_up_on: tuple[type[BaseException], ...] = (),
):
    """
    Decorator: retry with exponential backoff.

    Exceptions in `give_up_on` are re-raised immediately (e.g. quota errors,
    where retrying only burns more quota).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except give_up_on:
                    raise
                except retry_on as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    wait_time = backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}): {e}. Retrying in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
            raise RuntimeError("unreachable")
        return wrapper
    return decorator
