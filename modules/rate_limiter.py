"""Rate limiter: Redis-backed with in-memory fallback."""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter(ABC):
    @abstractmethod
    def is_allowed(self, ip: str) -> bool: ...


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis_url: str, max_requests: int, window_seconds: int) -> None:
        import redis as redis_lib

        self._r = redis_lib.from_url(redis_url)
        self._max = max_requests
        self._window = window_seconds

    def is_allowed(self, ip: str) -> bool:
        try:
            key = f"ratelimit:{ip}:{int(time.time()) // self._window}"
            pipe = self._r.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._window)
            count, _ = pipe.execute()
            return count <= self._max
        except Exception as exc:
            logger.warning("Redis rate-limit error: %s — allowing request.", exc)
            return True


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._windows: dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            ts = self._windows[ip]
            self._windows[ip] = [t for t in ts if now - t < self._window]
            if len(self._windows[ip]) >= self._max:
                return False
            self._windows[ip].append(now)
            return True


def create_rate_limiter(max_requests: int, window_seconds: int) -> RateLimiter:
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            limiter = RedisRateLimiter(redis_url, max_requests, window_seconds)
            limiter._r.ping()
            logger.info("Rate limiter: Redis")
            return limiter
        except Exception as exc:
            logger.warning("Redis unavailable for rate limiter (%s) — using in-memory.", exc)
    logger.info("Rate limiter: in-memory")
    return InMemoryRateLimiter(max_requests, window_seconds)
