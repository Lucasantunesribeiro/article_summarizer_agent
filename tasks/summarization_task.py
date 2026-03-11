"""Celery task for article summarisation."""
from __future__ import annotations

import logging
from datetime import datetime

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=5)
def summarize_article(self, task_id: str, url: str, method: str, length: str) -> dict:
    """Run the full summarisation pipeline as a Celery task."""
    from database import SessionLocal
    from models import Task

    db = SessionLocal()
    try:
        # Update status to processing
        task_row = db.query(Task).filter(Task.id == task_id).first()
        if task_row:
            task_row.status = "processing"
            db.commit()

        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run(url, method=method, length=length)

        if task_row:
            if result.get("success"):
                task_row.status = "done"
                task_row.summary = result.get("summary", "")
                task_row.method_used = result.get("method_used", "")
                task_row.execution_time = result.get("execution_time", 0)
                task_row.statistics = result.get("statistics", {})
                task_row.files_created = result.get("files_created", {})
            else:
                task_row.status = "failed"
                task_row.error = result.get("error", "Unknown error")
            task_row.finished_at = datetime.utcnow()
            db.commit()

        return result

    except Exception as exc:
        logger.error("Celery task %s failed: %s", task_id, exc)
        if db:
            task_row = db.query(Task).filter(Task.id == task_id).first()
            if task_row:
                task_row.status = "error"
                task_row.error = str(exc)
                task_row.finished_at = datetime.utcnow()
                db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
