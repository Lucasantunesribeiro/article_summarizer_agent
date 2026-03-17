"""Module-level Prometheus metrics registry."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

SUMMARIZATION_REQUESTS = Counter(
    "summarization_requests_total",
    "Total summarisation requests",
    ["status", "method"],
    registry=REGISTRY,
)

ACTIVE_TASKS = Gauge(
    "active_tasks_gauge",
    "Currently active summarisation tasks",
    registry=REGISTRY,
)

SUMMARIZATION_DURATION = Histogram(
    "summarization_duration_seconds",
    "Summarisation task duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=REGISTRY,
)
