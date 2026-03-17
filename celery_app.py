"""Celery application factory."""

from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"),
)
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/2"))

celery = Celery(
    "summarizer",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["tasks.summarization_task", "tasks.outbox_relay"],
)

import os as _os

if _os.getenv("OTEL_ENABLED", "false").lower() == "true":
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
    except ImportError:
        pass

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_queues={
        "celery": {
            "exchange": "celery",
            "routing_key": "celery",
        },
        "dead_letter": {
            "exchange": "dead_letter",
            "routing_key": "dead_letter",
        },
    },
    beat_schedule={
        "outbox-relay": {
            "task": "tasks.outbox_relay.relay_outbox_events",
            "schedule": 30.0,
        },
    },
)
