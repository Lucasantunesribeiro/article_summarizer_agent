"""
DB integration tests — require a real PostgreSQL instance.

Run with: make test-db
These tests are excluded from the regular `make test` run to avoid requiring
PostgreSQL in CI environments without Postgres.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

pytest.importorskip("pytest_postgresql", reason="pytest-postgresql not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(db_session, **kwargs):
    """Insert a Task row and return it."""
    from models import Task

    defaults = {
        "id": str(uuid.uuid4()),
        "status": "queued",
        "url": "https://example.com/article",
        "method": "extractive",
        "length": "medium",
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    task = Task(**defaults)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_and_fetch_task(db_session):
    """A task created in the DB can be retrieved by its ID."""
    from models import Task

    task = _make_task(db_session)
    fetched = db_session.query(Task).filter(Task.id == task.id).first()
    assert fetched is not None
    assert fetched.id == task.id
    assert fetched.status == "queued"
    assert fetched.url == "https://example.com/article"


def test_update_task_status(db_session):
    """Updating a task status persists correctly."""
    task = _make_task(db_session)
    task.status = "done"
    task.finished_at = datetime.utcnow()
    db_session.commit()

    db_session.expire(task)
    assert task.status == "done"
    assert task.finished_at is not None


def test_query_by_status_done(db_session):
    """Filtering by status=done returns only matching rows."""
    from models import Task

    _make_task(db_session, status="done")
    _make_task(db_session, status="done")
    _make_task(db_session, status="failed")

    done_tasks = db_session.query(Task).filter(Task.status == "done").all()
    assert len(done_tasks) == 2


def test_query_by_status_failed(db_session):
    """Filtering by status=failed returns only matching rows."""
    from models import Task

    _make_task(db_session, status="done")
    _make_task(db_session, status="failed")
    _make_task(db_session, status="failed")

    failed = db_session.query(Task).filter(Task.status == "failed").all()
    assert len(failed) == 2


def test_to_dict_returns_expected_fields(db_session):
    """to_dict() returns all expected keys."""
    task = _make_task(db_session, status="done", summary="Short summary.")
    d = task.to_dict()

    expected_keys = {
        "id", "status", "url", "method", "length",
        "created_at", "finished_at", "summary", "error",
        "statistics", "files_created", "method_used", "execution_time",
    }
    assert expected_keys.issubset(d.keys())
    assert d["status"] == "done"
    assert d["summary"] == "Short summary."


def test_statistics_json_roundtrip(db_session):
    """JSON statistics field serializes and deserializes correctly."""
    stats = {"words_original": 500, "words_summary": 80, "compression_ratio": 0.16}
    task = _make_task(db_session, statistics=stats)

    db_session.expire(task)
    assert task.statistics == stats
    assert task.statistics["compression_ratio"] == pytest.approx(0.16)


def test_files_created_json_roundtrip(db_session):
    """JSON files_created field round-trips correctly."""
    files = {"txt": "/outputs/abc.txt", "md": "/outputs/abc.md", "json": "/outputs/abc.json"}
    task = _make_task(db_session, files_created=files)

    db_session.expire(task)
    assert task.files_created == files
    assert "txt" in task.files_created


def test_multiple_tasks_ordering(db_session):
    """Tasks can be ordered by created_at descending."""
    from datetime import timedelta

    from models import Task

    now = datetime.utcnow()
    _make_task(db_session, created_at=now - timedelta(seconds=10))
    _make_task(db_session, created_at=now)
    _make_task(db_session, created_at=now - timedelta(seconds=5))

    ordered = db_session.query(Task).order_by(Task.created_at.desc()).all()
    times = [t.created_at for t in ordered]
    assert times == sorted(times, reverse=True)


def test_pagination_offset_limit(db_session):
    """offset/limit pagination returns correct subsets."""
    from models import Task

    for _ in range(5):
        _make_task(db_session, status="done")

    page1 = (
        db_session.query(Task)
        .filter(Task.status == "done")
        .order_by(Task.created_at.desc())
        .offset(0)
        .limit(2)
        .all()
    )
    page2 = (
        db_session.query(Task)
        .filter(Task.status == "done")
        .order_by(Task.created_at.desc())
        .offset(2)
        .limit(2)
        .all()
    )

    assert len(page1) == 2
    assert len(page2) == 2
    # Pages must not overlap
    ids_page1 = {t.id for t in page1}
    ids_page2 = {t.id for t in page2}
    assert ids_page1.isdisjoint(ids_page2)
