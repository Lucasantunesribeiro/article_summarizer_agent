"""
Unit tests for critical utility functions in app.py.
No real HTTP calls, no real agent — pure in-process logic.

Covers:
  - _normalise_url  (URL normalisation helper)
  - InMemoryRateLimiter (per-IP in-memory rate limiter, now in modules/rate_limiter.py)
  - _evict_old_tasks  (in-memory task store eviction)
"""

from __future__ import annotations

import os

# app.py raises RuntimeError when SECRET_KEY is absent in non-debug mode.
# Set these env vars before the first import of app so the module loads cleanly.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("FLASK_DEBUG", "true")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import time
from datetime import datetime, timedelta

from app import (
    _evict_old_tasks,
    _lock,
    _normalise_url,
    _results,
    _tasks,
)
from modules.rate_limiter import InMemoryRateLimiter
from config import config

# ---------------------------------------------------------------------------
# _normalise_url
# ---------------------------------------------------------------------------


class TestNormaliseUrl:
    def test_adds_https_to_bare_domain(self):
        assert _normalise_url("example.com") == "https://example.com"

    def test_strips_www_from_bare_input(self):
        # www. is stripped only when there is no scheme yet
        assert _normalise_url("www.example.com") == "https://example.com"

    def test_preserves_https_www(self):
        # When a scheme is already present the www. is left untouched
        assert _normalise_url("https://www.example.com") == "https://www.example.com"

    def test_preserves_existing_https(self):
        assert _normalise_url("https://example.com/path") == "https://example.com/path"

    def test_preserves_http(self):
        assert _normalise_url("http://example.com") == "http://example.com"

    def test_strips_whitespace(self):
        assert _normalise_url("  example.com  ") == "https://example.com"


# ---------------------------------------------------------------------------
# InMemoryRateLimiter (replaces old _check_rate_limit)
# ---------------------------------------------------------------------------


class TestRateLimit:
    def _make_limiter(self, max_requests=10, window_seconds=60):
        return InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    def test_first_request_allowed(self):
        limiter = self._make_limiter()
        assert limiter.is_allowed("10.0.0.1") is True

    def test_requests_within_limit_allowed(self):
        limiter = self._make_limiter(max_requests=10)
        ip = "10.0.0.2"
        for _ in range(5):
            assert limiter.is_allowed(ip) is True

    def test_exceeds_limit_returns_false(self):
        limiter = self._make_limiter(max_requests=3, window_seconds=60)
        ip = "10.0.0.3"
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        # 4th request must be rejected
        assert limiter.is_allowed(ip) is False

    def test_old_timestamps_evicted(self):
        limiter = self._make_limiter(max_requests=2, window_seconds=1)
        ip = "10.0.0.4"
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        # Already at the limit — 3rd should be rejected
        assert limiter.is_allowed(ip) is False
        # Wait for the 1-second window to expire
        time.sleep(1.1)
        # After eviction the old timestamps are gone; new request is allowed
        assert limiter.is_allowed(ip) is True


# ---------------------------------------------------------------------------
# _evict_old_tasks
# ---------------------------------------------------------------------------


class TestEvictOldTasks:
    def setup_method(self):
        with _lock:
            _tasks.clear()
            _results.clear()

    def test_no_eviction_when_under_limit(self):
        with _lock:
            for i in range(5):
                _tasks[str(i)] = {
                    "created_at": datetime.now().isoformat(),
                    "status": "done",
                }
        _evict_old_tasks(max_tasks=10)
        assert len(_tasks) == 5

    def test_evicts_oldest_tasks_over_limit(self):
        now = datetime.now()
        with _lock:
            # 3 old tasks — created hours in the past
            for i in range(3):
                _tasks[f"old_{i}"] = {
                    "created_at": (now - timedelta(hours=i + 1)).isoformat(),
                    "status": "done",
                }
            # 2 recent tasks — created right now
            for i in range(2):
                _tasks[f"new_{i}"] = {
                    "created_at": now.isoformat(),
                    "status": "done",
                }
        _evict_old_tasks(max_tasks=2)
        assert len(_tasks) == 2
        # Only the 2 newest entries should survive
        for key in _tasks:
            assert key.startswith("new_")
