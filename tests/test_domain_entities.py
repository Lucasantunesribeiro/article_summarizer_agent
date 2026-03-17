"""Domain entity unit tests."""

from __future__ import annotations

import pytest

from domain.entities import (
    SummarizationTask,
    TaskId,
    TaskStatus,
    TaskTransitionError,
    User,
    UserRole,
)


def make_task(**kwargs) -> SummarizationTask:
    defaults = {
        "id": "00000000-0000-0000-0000-000000000001",
        "url": "https://example.com",
        "method": "extractive",
        "length": "medium",
    }
    defaults.update(kwargs)
    return SummarizationTask(**defaults)


class TestTaskStateMachine:
    def test_initial_status_is_queued(self):
        task = make_task()
        assert task.status == TaskStatus.QUEUED

    def test_valid_transition_queued_to_processing(self):
        task = make_task()
        task.mark_processing()
        assert task.status == TaskStatus.PROCESSING
        assert task.progress == 10

    def test_valid_transition_processing_to_done(self):
        task = make_task(status=TaskStatus.PROCESSING)
        task.mark_completed({"summary": "s", "method_used": "extractive", "execution_time": 1.0})
        assert task.status == TaskStatus.DONE
        assert task.progress == 100

    def test_valid_transition_processing_to_failed(self):
        task = make_task(status=TaskStatus.PROCESSING)
        task.mark_failed("error")
        assert task.status == TaskStatus.FAILED
        assert task.error == "error"

    def test_invalid_transition_done_to_failed(self):
        task = make_task(status=TaskStatus.DONE)
        with pytest.raises(TaskTransitionError):
            task.mark_failed("error")

    def test_invalid_transition_done_to_processing(self):
        task = make_task(status=TaskStatus.DONE)
        with pytest.raises(TaskTransitionError):
            task.mark_processing()

    def test_invalid_transition_queued_to_done(self):
        task = make_task()
        with pytest.raises(TaskTransitionError):
            task.mark_completed({})


class TestTaskProperties:
    def test_is_terminal_done(self):
        task = make_task(status=TaskStatus.DONE)
        assert task.is_terminal is True

    def test_is_terminal_error(self):
        task = make_task(status=TaskStatus.ERROR)
        assert task.is_terminal is True

    def test_is_terminal_false_for_processing(self):
        task = make_task(status=TaskStatus.PROCESSING)
        assert task.is_terminal is False

    def test_is_pending(self):
        task = make_task()
        assert task.is_pending is True
        task.mark_processing()
        assert task.is_pending is False

    def test_can_retry(self):
        task = make_task(status=TaskStatus.FAILED)
        assert task.can_retry is True
        task2 = make_task(status=TaskStatus.DONE)
        assert task2.can_retry is False


class TestTaskId:
    def test_valid_uuid(self):
        tid = TaskId("00000000-0000-0000-0000-000000000001")
        assert str(tid) == "00000000-0000-0000-0000-000000000001"

    def test_invalid_uuid_raises(self):
        with pytest.raises(ValueError):
            TaskId("not-a-uuid")

    def test_frozen(self):
        tid = TaskId("00000000-0000-0000-0000-000000000001")
        with pytest.raises((AttributeError, TypeError)):
            tid.value = "other"  # type: ignore[misc]


class TestUserLifecycle:
    def test_activate_deactivate(self):
        user = User(
            id="u1",
            username="test",
            password_hash="hash",
            role=UserRole.ADMIN,
            is_active=False,
        )
        user.activate()
        assert user.is_active is True
        user.deactivate()
        assert user.is_active is False

    def test_can_manage_system_requires_active_admin(self):
        user = User(
            id="u1",
            username="test",
            password_hash="hash",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert user.can_manage_system() is True
        user.deactivate()
        assert user.can_manage_system() is False
