"""Integration tests for the outbox relay task.

These tests verify the relay's publish/fail logic without a real broker:
- successful publish marks entries as published
- failed publish increments retry_count and marks entry as failed
- entries exceeding MAX_RETRY_COUNT are moved to failed (DLQ)

Skipped automatically when celery is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

celery = pytest.importorskip("celery", reason="celery not installed")


def _make_entry(entry_id: str, retry_count: int = 0):
    entry = MagicMock()
    entry.id = entry_id
    entry.event_type = "task_completed"
    entry.aggregate_id = "agg-123"
    entry.payload = {"url": "https://example.com"}
    entry.retry_count = retry_count
    return entry


class TestOutboxRelayPublishSuccess:
    def test_publishes_pending_entries_and_marks_published(self):
        """Relay calls mark_published for each successfully published entry."""
        from tasks.outbox_relay import relay_outbox_events

        entry = _make_entry("entry-1")
        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = [entry]

        with (
            patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo),
            patch("tasks.outbox_relay._get_amqp_url", return_value=""),
        ):
            result = relay_outbox_events.apply().get()

        mock_repo.mark_published.assert_called_once_with("entry-1")
        mock_repo.mark_failed.assert_not_called()
        assert result["published"] == 1
        assert result["failed"] == 0

    def test_publishes_via_amqp_when_connection_available(self):
        """When a connection is available, _publish is called before mark_published."""
        from tasks.outbox_relay import relay_outbox_events

        entry = _make_entry("entry-2")
        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = [entry]

        mock_conn = MagicMock()

        with (
            patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo),
            patch("tasks.outbox_relay._get_amqp_url", return_value="amqp://localhost/"),
            patch("tasks.outbox_relay._open_connection", return_value=mock_conn),
            patch("tasks.outbox_relay._publish") as mock_publish,
        ):
            result = relay_outbox_events.apply().get()

        mock_publish.assert_called_once_with(
            mock_conn, "task_completed", "agg-123", {"url": "https://example.com"}
        )
        mock_repo.mark_published.assert_called_once_with("entry-2")
        assert result["published"] == 1

    def test_empty_pending_returns_zero_counts(self):
        """When no pending entries exist, relay returns zeros."""
        from tasks.outbox_relay import relay_outbox_events

        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = []

        with patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo):
            result = relay_outbox_events.apply().get()

        assert result == {"published": 0, "failed": 0, "total_pending": 0}


class TestOutboxRelayFailure:
    def test_failed_publish_increments_retry_count(self):
        """When _publish raises, entry is marked failed (retry_count incremented by repo)."""
        from tasks.outbox_relay import relay_outbox_events

        entry = _make_entry("entry-3")
        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = [entry]

        mock_conn = MagicMock()

        with (
            patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo),
            patch("tasks.outbox_relay._get_amqp_url", return_value="amqp://localhost/"),
            patch("tasks.outbox_relay._open_connection", return_value=mock_conn),
            patch("tasks.outbox_relay._publish", side_effect=ConnectionError("broker down")),
        ):
            result = relay_outbox_events.apply().get()

        mock_repo.mark_failed.assert_called_once_with("entry-3")
        mock_repo.mark_published.assert_not_called()
        assert result["failed"] == 1
        assert result["published"] == 0

    def test_entries_exceeding_max_retries_are_dead_lettered(self):
        """Entries with retry_count >= MAX_RETRY_COUNT are marked failed without publish attempt."""
        from tasks.outbox_relay import _MAX_RETRY_COUNT, relay_outbox_events

        # Entry already at the retry limit
        entry = _make_entry("entry-dlq", retry_count=_MAX_RETRY_COUNT)
        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = [entry]

        with (
            patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo),
            patch("tasks.outbox_relay._get_amqp_url", return_value=""),
            patch("tasks.outbox_relay._publish") as mock_publish,
        ):
            result = relay_outbox_events.apply().get()

        # Must NOT attempt to publish
        mock_publish.assert_not_called()
        # Must mark as failed (dead-letter)
        mock_repo.mark_failed.assert_called_once_with("entry-dlq")
        mock_repo.mark_published.assert_not_called()
        assert result["failed"] == 1

    def test_mixed_entries_published_and_failed(self):
        """Relay handles a batch with both successful and failed entries."""
        from tasks.outbox_relay import relay_outbox_events

        ok_entry = _make_entry("entry-ok")
        fail_entry = _make_entry("entry-fail")

        mock_repo = MagicMock()
        mock_repo.get_pending.return_value = [ok_entry, fail_entry]

        call_count = [0]

        def maybe_fail(conn, event_type, aggregate_id, payload):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("publish error")

        with (
            patch("tasks.outbox_relay.SqlAlchemyOutboxRepository", return_value=mock_repo),
            patch("tasks.outbox_relay._get_amqp_url", return_value="amqp://localhost/"),
            patch("tasks.outbox_relay._open_connection", return_value=MagicMock()),
            patch("tasks.outbox_relay._publish", side_effect=maybe_fail),
        ):
            result = relay_outbox_events.apply().get()

        assert result["published"] == 1
        assert result["failed"] == 1
