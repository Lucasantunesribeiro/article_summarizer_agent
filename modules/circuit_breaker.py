"""
Circuit Breaker — per-hostname resilience pattern
==================================================

Three states:
  CLOSED    — normal; requests pass through.
  OPEN      — failing; requests are rejected immediately.
  HALF_OPEN — testing recovery; one probe request is allowed.

Threshold: ``failure_threshold`` consecutive failures within ``window_seconds``
→ OPEN for ``timeout_seconds``, then HALF_OPEN.

Usage::

    cb = CircuitBreaker()
    hostname = "example.com"

    if cb.is_open(hostname):
        raise CircuitOpenError(hostname)
    try:
        result = make_request(hostname)
        cb.record_success(hostname)
    except Exception:
        cb.record_failure(hostname)
        raise
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum


class _State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a request is rejected because the circuit is OPEN."""

    def __init__(self, hostname: str) -> None:
        self.hostname = hostname
        super().__init__(f"Circuit breaker OPEN for {hostname!r} — request rejected.")


@dataclass
class _HostState:
    state: _State = _State.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float = 0.0


class CircuitBreaker:
    """Thread-safe circuit breaker keyed by hostname."""

    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_seconds: int = 120,
        window_seconds: int = 60,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._timeout_seconds = timeout_seconds
        self._window_seconds = window_seconds
        self._hosts: dict[str, _HostState] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_open(self, hostname: str) -> bool:
        """Return True if the circuit is OPEN (request should be rejected)."""
        with self._lock:
            state = self._get_state(hostname)
            return state.state == _State.OPEN

    def record_success(self, hostname: str) -> None:
        """Mark a successful request — reset failure count; close circuit."""
        with self._lock:
            s = self._get_state(hostname)
            s.state = _State.CLOSED
            s.failure_count = 0
            s.last_failure_time = 0.0

    def record_failure(self, hostname: str) -> None:
        """Mark a failed request — may trip the circuit to OPEN."""
        with self._lock:
            s = self._get_state(hostname)
            now = time.monotonic()

            # Reset counter if the last failure is outside the window
            if now - s.last_failure_time > self._window_seconds:
                s.failure_count = 0

            s.failure_count += 1
            s.last_failure_time = now

            if s.failure_count >= self._failure_threshold:
                s.state = _State.OPEN
                s.opened_at = now

    def get_status(self, hostname: str) -> dict:
        """Return diagnostic info for *hostname*."""
        with self._lock:
            s = self._get_state(hostname)
            now = time.monotonic()
            remaining = max(0.0, self._timeout_seconds - (now - s.opened_at))
            return {
                "hostname": hostname,
                "state": s.state.value,
                "failure_count": s.failure_count,
                "seconds_until_retry": round(remaining, 1) if s.state == _State.OPEN else 0,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_state(self, hostname: str) -> _HostState:
        """Return (and lazily create) state for *hostname*; advance OPEN→HALF_OPEN if timeout elapsed."""
        if hostname not in self._hosts:
            self._hosts[hostname] = _HostState()

        s = self._hosts[hostname]

        if s.state == _State.OPEN:
            now = time.monotonic()
            if now - s.opened_at >= self._timeout_seconds:
                # Allow one probe request
                s.state = _State.HALF_OPEN

        return s


# Module-level singleton (shared across all WebScraper instances)
circuit_breaker = CircuitBreaker()
