"""Testes da política de retry (modules/retry.py) — sem dormir de verdade."""

from __future__ import annotations

import email.utils

import pytest

from modules.retry import (
    RetryBudgetExceeded,
    RetryDecision,
    RetryPolicy,
    backoff_delay,
    parse_retry_after,
    retry_call,
)


class Transient(Exception):
    def __init__(self, retry_after=None):
        super().__init__("transient")
        self.retry_after = retry_after


class Permanent(Exception):
    pass


def classify(exc):
    if isinstance(exc, Transient):
        return RetryDecision(retryable=True, retry_after=exc.retry_after)
    return RetryDecision(retryable=False)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def failing(n, exc_factory, result="ok"):
    calls = {"count": 0, "remaining": []}

    def fn(remaining):
        calls["count"] += 1
        calls["remaining"].append(remaining)
        if calls["count"] <= n:
            raise exc_factory()
        return result

    return fn, calls


def run(fn, policy, clock, rng=lambda: 1.0):
    return retry_call(fn, policy=policy, classify=classify, sleep=clock.sleep, clock=clock, rng=rng)


class TestRetryCall:
    def test_succeeds_after_transient_failures(self):
        clock = FakeClock()
        fn, calls = failing(2, Transient)
        policy = RetryPolicy(max_attempts=3, base_delay=1, max_delay=10, total_timeout=60)

        assert run(fn, policy, clock) == "ok"
        assert calls["count"] == 3
        # backoff exponencial (rng=1.0 → teto): 1s, 2s
        assert clock.sleeps == [1.0, 2.0]

    def test_permanent_error_is_not_retried(self):
        clock = FakeClock()
        fn, calls = failing(5, Permanent)
        policy = RetryPolicy(max_attempts=5, base_delay=1, max_delay=10, total_timeout=60)

        with pytest.raises(Permanent):
            run(fn, policy, clock)
        assert calls["count"] == 1
        assert clock.sleeps == []

    def test_gives_up_after_max_attempts(self):
        clock = FakeClock()
        fn, calls = failing(10, Transient)
        policy = RetryPolicy(max_attempts=3, base_delay=1, max_delay=10, total_timeout=60)

        with pytest.raises(Transient):
            run(fn, policy, clock)
        assert calls["count"] == 3
        assert len(clock.sleeps) == 2

    def test_retry_after_overrides_backoff(self):
        clock = FakeClock()
        fn, calls = failing(1, lambda: Transient(retry_after=7.5))
        policy = RetryPolicy(max_attempts=3, base_delay=1, max_delay=2, total_timeout=60)

        assert run(fn, policy, clock) == "ok"
        assert clock.sleeps == [7.5]

    def test_retry_after_beyond_budget_stops_immediately(self):
        clock = FakeClock()
        fn, calls = failing(1, lambda: Transient(retry_after=120))
        policy = RetryPolicy(max_attempts=5, base_delay=1, max_delay=2, total_timeout=30)

        with pytest.raises(RetryBudgetExceeded) as info:
            run(fn, policy, clock)
        assert isinstance(info.value.__cause__, Transient)
        assert calls["count"] == 1
        assert clock.sleeps == []

    def test_total_timeout_caps_attempts(self):
        clock = FakeClock()
        fn, calls = failing(100, Transient)
        policy = RetryPolicy(max_attempts=100, base_delay=4, max_delay=4, total_timeout=10)

        with pytest.raises(RetryBudgetExceeded):
            run(fn, policy, clock)
        assert sum(clock.sleeps) < 10
        assert calls["count"] == 3  # 0s, 4s, 8s; a espera seguinte estouraria 10s

    def test_fn_receives_remaining_budget(self):
        clock = FakeClock()
        fn, calls = failing(1, Transient)
        policy = RetryPolicy(max_attempts=3, base_delay=2, max_delay=2, total_timeout=30)

        run(fn, policy, clock)
        assert calls["remaining"] == [30.0, 28.0]

    def test_jitter_spreads_delay_within_cap(self):
        policy = RetryPolicy(max_attempts=10, base_delay=1, max_delay=8, total_timeout=100)
        assert backoff_delay(1, policy, rng=lambda: 0.5) == 0.5
        assert backoff_delay(3, policy, rng=lambda: 0.25) == 1.0
        assert backoff_delay(10, policy, rng=lambda: 1.0) == 8.0  # limitado por max_delay
        assert backoff_delay(2, policy, rng=lambda: 0.0) == 0.0

    def test_invalid_policy(self):
        with pytest.raises(ValueError):
            RetryPolicy(max_attempts=0)
        with pytest.raises(ValueError):
            RetryPolicy(total_timeout=0)


class TestParseRetryAfter:
    def test_seconds(self):
        assert parse_retry_after("12") == 12.0

    def test_negative_clamped(self):
        assert parse_retry_after("-3") == 0.0

    def test_http_date(self):
        now = 1_700_000_000.0
        header = email.utils.formatdate(now + 30, usegmt=True)
        assert parse_retry_after(header, now=now) == pytest.approx(30, abs=1)

    @pytest.mark.parametrize("value", [None, "", "soon", "Mon, 99 Foo"])
    def test_invalid(self, value):
        assert parse_retry_after(value) is None
