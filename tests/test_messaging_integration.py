"""Integration tests for Celery task dispatch and AsyncTaskDispatcher fallback.

These tests verify:
- Celery task runs correctly in eager mode (no real broker required)
- AsyncTaskDispatcher falls back to thread when Celery is unavailable

Skipped automatically when celery is not installed.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

pytest = __import__("pytest")
celery_mod = pytest.importorskip("celery", reason="celery not installed")


class TestCeleryTaskEagerMode:
    """Run Celery task in ALWAYS_EAGER mode — no broker required."""

    def test_summarize_article_completes_in_eager_mode(self):
        """Celery task calls process_task_handler and returns its result in eager mode."""
        from celery_app import celery

        mock_result = {
            "task_id": "task-eager-1",
            "status": "done",
            "summary": "Eager summary",
        }
        mock_container = MagicMock()
        mock_container.process_task_handler.handle.return_value = mock_result

        celery.conf.task_always_eager = True
        celery.conf.task_eager_propagates = True

        try:
            with patch(
                "tasks.summarization_task.build_runtime_container",
                return_value=mock_container,
            ):
                from tasks.summarization_task import summarize_article

                result = summarize_article.delay(
                    "task-eager-1", "https://example.com", "extractive", "medium"
                ).get()

            mock_container.process_task_handler.handle.assert_called_once_with(
                "task-eager-1", "https://example.com", "extractive", "medium"
            )
            assert result == mock_result
        finally:
            celery.conf.task_always_eager = False


class TestAsyncTaskDispatcherFallback:
    """AsyncTaskDispatcher must fall back to daemon thread when Celery is unavailable."""

    def test_falls_back_to_thread_when_celery_unavailable(self):
        """When Celery ping fails, dispatch runs in a daemon thread."""
        done_event = threading.Event()
        call_args = {}

        def fake_handle(task_id, url, method, length):
            call_args.update(
                {"task_id": task_id, "url": url, "method": method, "length": length}
            )
            done_event.set()

        mock_handler = MagicMock()
        mock_handler.handle.side_effect = fake_handle

        # Patch the inspect call inside celery_app module
        with patch("celery_app.celery.control.inspect") as mock_inspect:
            mock_inspect.return_value.ping.side_effect = Exception("no broker")
            from infrastructure.container import AsyncTaskDispatcher

            dispatcher = AsyncTaskDispatcher(mock_handler)

        assert dispatcher._celery_available is False

        dispatcher.dispatch("task-thread-1", "https://example.com", "extractive", "medium")

        done = done_event.wait(timeout=5.0)
        assert done, "Thread did not complete in time"
        assert call_args["task_id"] == "task-thread-1"
        assert call_args["url"] == "https://example.com"

    def test_prefers_celery_when_available(self):
        """When Celery is reachable, dispatch sends task via Celery, not a thread."""
        mock_handler = MagicMock()

        with patch("celery_app.celery.control.inspect") as mock_inspect:
            mock_inspect.return_value.ping.return_value = {"worker": "pong"}
            from infrastructure.container import AsyncTaskDispatcher

            dispatcher = AsyncTaskDispatcher(mock_handler)

        assert dispatcher._celery_available is True

        with patch("tasks.summarization_task.summarize_article.delay") as mock_delay:
            dispatcher.dispatch("task-celery-1", "https://example.com", "extractive", "medium")
            mock_delay.assert_called_once_with(
                "task-celery-1", "https://example.com", "extractive", "medium"
            )
