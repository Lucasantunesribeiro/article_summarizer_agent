"""
Secrets manager with JWT key rotation and grace-period verification.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import threading
import time
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_GRACE = 3600


class SecretsManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._redis = self._connect_redis()
        initial_secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "")
        if not initial_secret:
            initial_secret = secrets.token_urlsafe(32)
            logger.warning("No JWT_SECRET_KEY set — generated ephemeral secret.")
        self._secrets: list[dict[str, object]] = [
            {
                "key_id": os.getenv("JWT_SECRET_KEY_ID", str(uuid4())),
                "secret": initial_secret,
                "expires_at": float("inf"),
                "created_at": time.time(),
            }
        ]
        if self._redis:
            self._load_from_redis()

    def get_current_secret(self) -> str:
        return self.get_current_key()["secret"]  # type: ignore[return-value]

    def get_current_key_id(self) -> str:
        return self.get_current_key()["key_id"]  # type: ignore[return-value]

    def get_current_key(self) -> dict[str, object]:
        self._evict_expired()
        with self._lock:
            return dict(self._secrets[0])

    def get_all_valid_keys(self) -> list[dict[str, object]]:
        self._evict_expired()
        with self._lock:
            return [dict(entry) for entry in self._secrets]

    def get_all_valid_secrets(self) -> list[str]:
        return [entry["secret"] for entry in self.get_all_valid_keys()]

    def get_secret_for_kid(self, key_id: str | None) -> str | None:
        self._evict_expired()
        if not key_id:
            return self.get_current_secret()
        with self._lock:
            for entry in self._secrets:
                if entry["key_id"] == key_id:
                    return entry["secret"]  # type: ignore[return-value]
        return None

    def rotate(self, new_secret: str | None = None, grace_period_seconds: int = DEFAULT_GRACE) -> dict:
        if not new_secret:
            new_secret = secrets.token_urlsafe(32)

        expires_at = time.time() + grace_period_seconds
        new_entry = {
            "key_id": str(uuid4()),
            "secret": new_secret,
            "expires_at": float("inf"),
            "created_at": time.time(),
        }

        with self._lock:
            if self._secrets:
                self._secrets[0]["expires_at"] = expires_at
            self._secrets.insert(0, new_entry)

        self._persist_to_redis()
        logger.info(
            "JWT secret rotated — key_id=%s grace=%ss", new_entry["key_id"], grace_period_seconds
        )
        return {
            "rotated": True,
            "active_key_id": new_entry["key_id"],
            "grace_period_seconds": grace_period_seconds,
            "expires_at": expires_at,
            "active_secrets": len(self.get_all_valid_keys()),
        }

    def _evict_expired(self) -> None:
        now = time.time()
        with self._lock:
            self._secrets = [
                entry for entry in self._secrets if float(entry["expires_at"]) > now
            ] or self._secrets[:1]

    def _connect_redis(self):
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return None
        try:
            import redis

            client = redis.from_url(redis_url)
            client.ping()
            return client
        except Exception as exc:
            logger.debug("Redis not available for secrets manager: %s", exc)
            return None

    def _persist_to_redis(self) -> None:
        if not self._redis:
            return
        try:
            with self._lock:
                payload = json.dumps(self._secrets)
            self._redis.set("jwt:secrets", payload, ex=86400 * 7)
        except Exception as exc:
            logger.warning("Failed to persist secrets to Redis: %s", exc)

    def _load_from_redis(self) -> None:
        if not self._redis:
            return
        try:
            raw = self._redis.get("jwt:secrets")
            if not raw:
                return
            loaded = json.loads(raw)
            if loaded:
                with self._lock:
                    self._secrets = loaded
        except Exception as exc:
            logger.warning("Failed to load secrets from Redis: %s", exc)


secrets_manager = SecretsManager()
