"""Celery task for article summarisation."""

from __future__ import annotations

import logging

from celery_app import celery
from infrastructure.container import build_runtime_container

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def summarize_article(self, task_id: str, url: str, method: str, length: str) -> dict:
    try:
        container = build_runtime_container()
        return container.process_task_handler.handle(task_id, url, method, length)
    except Exception as exc:
        logger.error("Celery task %s failed: %s", task_id, exc)
        raise self.retry(exc=exc) from exc
