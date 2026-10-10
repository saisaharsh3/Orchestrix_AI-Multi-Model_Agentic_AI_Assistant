"""Logger, rate limiter, retry and user preferences."""

import time

import pytest

from config.settings import UserPreferences
from core.logger import get_logger
from core.rate_limiter import RateLimiter, with_rate_limit, with_retry


class TestLogger:
    def test_handlers_are_attached_once(self):
        import logging
        before = len(logging.getLogger().handlers)
        get_logger("a")
        get_logger("b")
        assert len(logging.getLogger().handlers) == before


class TestRateLimiter:
    def test_interval(self):
        assert RateLimiter(calls_per_minute=60).min_interval == 1.0

    def test_waits_between_calls(self):
        limiter = RateLimiter(calls_per_minute=120)  # 0.5 s
        start = time.time()
        limiter.wait_if_needed("svc")
        limiter.wait_if_needed("svc")
        assert time.time() - start >= 0.4

    def test_services_are_independent(self):
        limiter = RateLimiter(calls_per_minute=1)
        limiter.wait_if_needed("a")
        start = time.time()
        limiter.wait_if_needed("b")
        assert time.time() - start < 0.1

    def test_reset(self):
        limiter = RateLimiter(calls_per_minute=1)
        limiter.wait_if_needed("svc")
        limiter.reset("svc")
        start = time.time()
        limiter.wait_if_needed("svc")
        assert time.time() - start < 0.1

    def test_decorator(self):
        limiter = RateLimiter(calls_per_minute=600)

        @with_rate_limit("svc", limiter)
        def f():
            return "done"

        assert f() == "done"


class TestRetry:
    def test_retries_until_success(self):
        attempts = 0

        @with_retry(max_attempts=3, backoff_factor=0.01)
        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RuntimeError("temporary")
            return "ok"

        assert flaky() == "ok"
        assert attempts == 2

    def test_raises_after_max_attempts(self):
        @with_retry(max_attempts=2, backoff_factor=0.01)
        def broken():
            raise RuntimeError("down")

        with pytest.raises(RuntimeError):
            broken()

    def test_give_up_on_is_not_retried(self):
        attempts = 0

        @with_retry(max_attempts=3, backoff_factor=0.01, give_up_on=(KeyError,))
        def quota():
            nonlocal attempts
            attempts += 1
            raise KeyError("quota")

        with pytest.raises(KeyError):
            quota()
        assert attempts == 1


class TestUserPreferences:
    def test_defaults_created_on_first_read(self):
        prefs = UserPreferences.get_user_prefs("u1")
        assert prefs["user_id"] == "u1"
        assert prefs["preferred_model"] in {"api", "local"}
        assert prefs["stealth_mode"] is False

    def test_set_pref_persists(self):
        UserPreferences.set_user_pref("u1", "preferred_model", "api")
        assert UserPreferences.get_user_prefs("u1")["preferred_model"] == "api"

    def test_users_are_separate(self):
        UserPreferences.toggle_stealth_mode("u1", True)
        assert UserPreferences.get_user_prefs("u2")["stealth_mode"] is False
