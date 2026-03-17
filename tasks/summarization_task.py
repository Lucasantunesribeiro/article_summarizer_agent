"""Celery task for article summarisation."""

from __future__ import annotations

import logging

from celery_app import celery
from infrastructure.container import build_runtime_container

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def summarize_article(self, task_id: str, url: str, method: str, length: str) -> dict:
    try:
        container = build_runtime_container()
        return container.process_task_handler.handle(task_id, url, method, length)
    except self.MaxRetriesExceededError:
        logger.error("Celery task %s exhausted all retries — writing to dead-letter.", task_id)
        try:
            _write_dead_letter(task_id)
        except Exception as dlq_exc:
            logger.warning("DLQ write failed for task %s: %s", task_id, dlq_exc)
        raise
    except Exception as exc:
        logger.error("Celery task %s failed (attempt %d): %s", task_id, self.request.retries, exc)
        raise


def _write_dead_letter(task_id: str) -> None:
    """Persist a dead-letter record so the task can be inspected and retried manually."""
    from database import session_scope
    from models import Task

    with session_scope() as session:
        row = session.query(Task).filter(Task.id == task_id).first()
        if row:
            row.status = "failed"
            row.message = "Exceeded maximum retry attempts; moved to dead-letter."
