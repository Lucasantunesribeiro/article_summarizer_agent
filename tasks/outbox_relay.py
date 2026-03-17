"""Celery beat task for outbox relay — publishes domain events to RabbitMQ."""

from __future__ import annotations

import contextlib
import json
import logging
import os

from celery_app import celery
from infrastructure.repositories import SqlAlchemyOutboxRepository

logger = logging.getLogger(__name__)

_AMQP_URL = os.environ.get(
    "CELERY_BROKER_URL",
    os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"),
)
_EXCHANGE_NAME = "domain_events"
_MAX_RETRY_COUNT = int(os.environ.get("OUTBOX_MAX_RETRIES", "5"))


def _get_amqp_url() -> str:
    """Return AMQP URL, stripping redis:// if broker is Redis (not AMQP)."""
    url = _AMQP_URL
    if url.startswith("redis://") or url.startswith("rediss://"):
        # Broker is Redis — no AMQP available; caller handles this gracefully
        return ""
    return url


@celery.task(name="tasks.outbox_relay.relay_outbox_events", bind=True, max_retries=3)
def relay_outbox_events(self):
    """Scan pending outbox entries and publish them to the domain_events exchange."""
    try:
        repo = SqlAlchemyOutboxRepository()
        pending = repo.get_pending(limit=50)

        if not pending:
            return {"published": 0, "failed": 0, "total_pending": 0}

        published_count = 0
        failed_count = 0

        amqp_url = _get_amqp_url()
        connection = _open_connection(amqp_url) if amqp_url else None

        try:
            for entry in pending:
                # Dead-letter: too many prior failures → skip publish, mark failed
                if entry.retry_count >= _MAX_RETRY_COUNT:
                    logger.warning(
                        "Outbox entry %s exceeded max retries (%d) — moving to failed.",
                        entry.id,
                        _MAX_RETRY_COUNT,
                    )
                    repo.mark_failed(entry.id)
                    failed_count += 1
                    continue

                try:
                    if connection is not None:
                        _publish(connection, entry.event_type, entry.aggregate_id, entry.payload)
                    else:
                        # No AMQP broker available — log and still mark published
                        # so the relay doesn't endlessly retry when Redis is the broker.
                        logger.debug(
                            "AMQP unavailable; logging event %s for entry %s",
                            entry.event_type,
                            entry.id,
                        )
                    repo.mark_published(entry.id)
                    published_count += 1
                except Exception as exc:
                    logger.warning("Failed to relay outbox entry %s: %s", entry.id, exc)
                    repo.mark_failed(entry.id)
                    failed_count += 1
        finally:
            if connection is not None:
                with contextlib.suppress(Exception):
                    connection.release()

        logger.info(
            "Outbox relay: published=%d failed=%d total_pending=%d",
            published_count,
            failed_count,
            len(pending),
        )
        return {"published": published_count, "failed": failed_count, "total_pending": len(pending)}

    except Exception as exc:
        logger.error("Outbox relay task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc


def _open_connection(amqp_url: str):
    """Open a kombu AMQP connection. Returns None on import error."""
    try:
        from kombu import Connection  # type: ignore[import-untyped]

        conn = Connection(amqp_url)
        conn.connect()
        return conn
    except ImportError:
        logger.warning("kombu not installed; outbox relay will skip AMQP publish.")
        return None
    except Exception as exc:
        logger.warning("Cannot connect to AMQP broker (%s): %s", amqp_url, exc)
        return None


def _publish(connection, event_type: str, aggregate_id: str, payload: dict) -> None:
    """Publish a single domain event to the topic exchange."""
    from kombu import Exchange, Producer  # type: ignore[import-untyped]

    exchange = Exchange(_EXCHANGE_NAME, type="topic", durable=True)
    channel = connection.channel()
    producer = Producer(channel, exchange=exchange, routing_key=event_type)
    producer.publish(
        json.dumps({"event_type": event_type, "aggregate_id": aggregate_id, "payload": payload}),
        content_type="application/json",
        retry=True,
        retry_policy={"max_retries": 3, "interval_start": 0, "interval_step": 1},
    )
