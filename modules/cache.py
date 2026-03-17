"""Cache abstraction: Redis backend with filesystem fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> dict | None: ...

    @abstractmethod
    def set(self, key: str, value: dict, ttl: int | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def clear_all(self) -> None: ...

    @staticmethod
    def make_key(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()


class RedisCacheBackend(CacheBackend):
    def __init__(self, redis_url: str, ttl: int = 86400) -> None:
        import redis as redis_lib

        self._r = redis_lib.from_url(redis_url, decode_responses=True)
        self._default_ttl = ttl

    def get(self, key: str) -> dict | None:
        try:
            raw = self._r.get(f"cache:{key}")
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("Redis get error: %s", exc)
            return None

    def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        try:
            self._r.setex(f"cache:{key}", ttl or self._default_ttl, json.dumps(value))
        except Exception as exc:
            logger.warning("Redis set error: %s", exc)

    def delete(self, key: str) -> None:
        try:
            self._r.delete(f"cache:{key}")
        except Exception as exc:
            logger.warning("Redis delete error: %s", exc)

    def clear_all(self) -> None:
        try:
            keys = self._r.keys("cache:*")
            if keys:
                self._r.delete(*keys)
        except Exception as exc:
            logger.warning("Redis clear error: %s", exc)


class FilesystemCacheBackend(CacheBackend):
    def __init__(self, cache_dir: str = ".cache", ttl: int = 86400) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, key: str) -> dict | None:
        import time

        p = self._path(key)
        if not p.exists():
            return None
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - p.stat().st_mtime > self._ttl:
                p.unlink(missing_ok=True)
                return None
            return data
        except Exception as exc:
            logger.warning("Filesystem cache get error: %s", exc)
            return None

    def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        try:
            with open(self._path(key), "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Filesystem cache set error: %s", exc)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def clear_all(self) -> None:
        for p in self._dir.glob("*.json"):
            p.unlink(missing_ok=True)


def create_cache_backend(ttl: int = 86400) -> CacheBackend:
    """Factory: Redis if REDIS_URL is set, else filesystem."""
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            backend = RedisCacheBackend(redis_url, ttl=ttl)
            backend._r.ping()
            logger.info("Cache backend: Redis (%s)", redis_url)
            return backend
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — falling back to filesystem cache.", exc)
    logger.info("Cache backend: filesystem")
    return FilesystemCacheBackend(ttl=ttl)
