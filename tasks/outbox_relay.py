"""Celery beat task for outbox relay."""

from __future__ import annotations

import logging

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="tasks.outbox_relay.relay_outbox_events", bind=True, max_retries=3)
def relay_outbox_events(self):
    """Scan pending outbox entries and publish them."""
    try:
        from infrastructure.repositories import SqlAlchemyOutboxRepository

        repo = SqlAlchemyOutboxRepository()
        pending = repo.get_pending(limit=50)

        published_count = 0
        for entry in pending:
            try:
                # In a full implementation, publish to RabbitMQ exchange here.
                # For now, mark as published to demonstrate the pattern.
                repo.mark_published(entry.id)
                published_count += 1
            except Exception as exc:
                logger.warning("Failed to relay outbox entry %s: %s", entry.id, exc)
                repo.mark_failed(entry.id)

        if published_count:
            logger.info("Outbox relay published %d events.", published_count)
        return {"published": published_count}
    except Exception as exc:
        logger.error("Outbox relay task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc
