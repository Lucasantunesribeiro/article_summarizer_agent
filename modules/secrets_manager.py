"""
Secrets Manager — JWT secret rotation with grace period
========================================================

Manages rotation of the JWT signing secret without downtime.

Rotation strategy:
- New secret becomes active immediately for *signing*.
- The previous secret is tracked for ``grace_period_seconds``.
- During the grace period, the ``/api/auth/refresh`` endpoint can be used
  to exchange an old-secret token for a new-secret token before expiry.
- ``get_all_valid_secrets()`` returns the full list for callers that can
  implement multi-key verification (e.g. RS256 with JWK sets). For the
  default HMAC/HS256 setup, ``get_current_secret()`` is used.

Storage backends (in order of preference):
1. Redis   — ``jwt:secrets`` key as a JSON list of {secret, expires_at} dicts.
2. Fallback in-memory — suitable for single-process dev; lost on restart.

Usage::

    from modules.secrets_manager import secrets_manager

    # In Flask-JWT-Extended hooks:
    @jwt.encode_key_loader
    def encode_key(identity):
        return secrets_manager.get_current_secret()

    @jwt.decode_key_loader
    def decode_key(jwt_header, jwt_data):
        return secrets_manager.get_current_secret()

Admin token multi-support::

    # ADMIN_TOKEN=token1,token2  (comma-separated)
    secrets_manager.is_admin_token_valid(request.headers.get("X-Admin-Token"))
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import threading
import time

logger = logging.getLogger(__name__)

_DEFAULT_GRACE = 3600  # seconds


class SecretsManager:
    """JWT secret rotation with Redis persistence and in-memory fallback."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # In-memory store: list of {"secret": str, "expires_at": float}
        # First element is always the current (newest) secret.
        _initial = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "")
        if not _initial:
            _initial = secrets.token_urlsafe(32)
            logger.warning("No JWT_SECRET_KEY set — generated ephemeral secret.")
        self._secrets: list[dict] = [{"secret": _initial, "expires_at": float("inf")}]
        self._redis = self._connect_redis()
        if self._redis:
            self._load_from_redis()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_secret(self) -> str:
        """Return the active secret used for signing new tokens."""
        self._evict_expired()
        with self._lock:
            return self._secrets[0]["secret"]

    def get_all_valid_secrets(self) -> list[str]:
        """Return all secrets still valid for verification (current + grace period)."""
        self._evict_expired()
        with self._lock:
            return [entry["secret"] for entry in self._secrets]

    def rotate(self, new_secret: str | None = None, grace_period_seconds: int = _DEFAULT_GRACE) -> dict:
        """Promote *new_secret* as the current signing key.

        The previous secret remains valid for verification for *grace_period_seconds*.
        If *new_secret* is None, a cryptographically random secret is generated.

        Returns metadata about the rotation.
        """
        if not new_secret:
            new_secret = secrets.token_urlsafe(32)

        expires_at = time.time() + grace_period_seconds

        with self._lock:
            # Mark existing current secret as expiring
            if self._secrets:
                self._secrets[0]["expires_at"] = expires_at
            # Prepend new current secret (never expires until next rotation)
            self._secrets.insert(0, {"secret": new_secret, "expires_at": float("inf")})

        if self._redis:
            self._persist_to_redis()

        logger.info(
            "JWT secret rotated — grace period %ds, expires_at %.0f", grace_period_seconds, expires_at
        )
        return {
            "rotated": True,
            "grace_period_seconds": grace_period_seconds,
            "expires_at": expires_at,
            "active_secrets": len(self._secrets),
        }

    def is_admin_token_valid(self, token: str) -> bool:
        """Validate *token* against ADMIN_TOKEN env var.

        Supports multiple tokens separated by commas:
            ADMIN_TOKEN=token1,token2
        """
        if not token:
            return False
        raw = os.getenv("ADMIN_TOKEN", "")
        if not raw:
            return False
        valid_tokens = {t.strip() for t in raw.split(",") if t.strip()}
        return token in valid_tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove entries past their expiry; always keep at least one (current)."""
        now = time.time()
        with self._lock:
            self._secrets = [
                e for e in self._secrets if e["expires_at"] > now
            ] or self._secrets[:1]

    def _connect_redis(self):
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return None
        try:
            import redis

            r = redis.from_url(redis_url)
            r.ping()
            return r
        except Exception as exc:
            logger.debug("Redis not available for secrets manager: %s", exc)
            return None

    def _persist_to_redis(self) -> None:
        if not self._redis:
            return
        try:
            with self._lock:
                payload = json.dumps(self._secrets)
            self._redis.set("jwt:secrets", payload, ex=86400 * 7)  # TTL 7 days
        except Exception as exc:
            logger.warning("Failed to persist secrets to Redis: %s", exc)

    def _load_from_redis(self) -> None:
        try:
            raw = self._redis.get("jwt:secrets")
            if not raw:
                return
            loaded: list[dict] = json.loads(raw)
            if loaded:
                with self._lock:
                    self._secrets = loaded
                logger.info("Loaded %d secrets from Redis.", len(loaded))
        except Exception as exc:
            logger.warning("Failed to load secrets from Redis: %s", exc)


# Module-level singleton
secrets_manager = SecretsManager()
