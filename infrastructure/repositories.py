"""SQLAlchemy repository implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import func

from database import session_scope
from domain.entities import (
    AuditLogEntry,
    OutboxEntry,
    SummarizationTask,
    TaskStatus,
    User,
    UserRole,
)
from domain.repositories import (
    AuditLogRepository,
    OutboxRepository,
    SettingsRepository,
    TaskRepository,
    UserRepository,
)
from models import AuditLog, Setting, Task
from models import OutboxEntry as OutboxEntryModel
from models import User as UserModel

SessionFactory = Callable[[], Any]


def _to_task_entity(model: Task) -> SummarizationTask:
    return SummarizationTask(
        id=model.id,
        url=model.url,
        method=model.method or "extractive",
        length=model.length or "medium",
        status=TaskStatus(model.status),
        progress=model.progress,
        message=model.message,
        created_at=model.created_at,
        finished_at=model.finished_at,
        summary=model.summary,
        error=model.error,
        statistics=model.statistics,
        files_created=model.files_created,
        method_used=model.method_used,
        execution_time=model.execution_time,
    )


def _to_user_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        username=model.username,
        password_hash=model.password_hash,
        role=UserRole(model.role),
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_login_at=model.last_login_at,
    )


class SqlAlchemyTaskRepository(TaskRepository):
    def add(self, task: SummarizationTask) -> None:
        with session_scope() as session:
            session.add(
                Task(
                    id=task.id,
                    status=task.status.value,
                    progress=task.progress,
                    message=task.message,
                    url=task.url,
                    method=task.method,
                    length=task.length,
                    created_at=task.created_at,
                    finished_at=task.finished_at,
                    summary=task.summary,
                    error=task.error,
                    statistics=task.statistics,
                    files_created=task.files_created,
                    method_used=task.method_used,
                    execution_time=task.execution_time,
                )
            )

    def update(self, task: SummarizationTask) -> None:
        with session_scope() as session:
            row = session.query(Task).filter(Task.id == task.id).first()
            if not row:
                self.add(task)
                return
            row.status = task.status.value
            row.progress = task.progress
            row.message = task.message
            row.finished_at = task.finished_at
            row.summary = task.summary
            row.error = task.error
            row.statistics = task.statistics
            row.files_created = task.files_created
            row.method_used = task.method_used
            row.execution_time = task.execution_time

    def get(self, task_id: str) -> SummarizationTask | None:
        with session_scope() as session:
            row = session.query(Task).filter(Task.id == task_id).first()
            return _to_task_entity(row) if row else None

    def list_recent(
        self, page: int = 1, per_page: int = 20, statuses: tuple[str, ...] | None = None
    ) -> tuple[list[SummarizationTask], int]:
        with session_scope() as session:
            query = session.query(Task)
            if statuses:
                query = query.filter(Task.status.in_(statuses))
            total = query.count()
            rows = (
                query.order_by(Task.created_at.desc())
                .offset(max(page - 1, 0) * per_page)
                .limit(per_page)
                .all()
            )
            return [_to_task_entity(row) for row in rows], total

    def get_statistics(self) -> dict[str, int]:
        with session_scope() as session:
            counts = {
                "total": session.query(func.count(Task.id)).scalar() or 0,
                "done": session.query(func.count(Task.id))
                .filter(Task.status == TaskStatus.DONE.value)
                .scalar()
                or 0,
                "failed": session.query(func.count(Task.id))
                .filter(Task.status.in_((TaskStatus.FAILED.value, TaskStatus.ERROR.value)))
                .scalar()
                or 0,
                "running": session.query(func.count(Task.id))
                .filter(Task.status.in_((TaskStatus.QUEUED.value, TaskStatus.PROCESSING.value)))
                .scalar()
                or 0,
            }
            return counts


class SqlAlchemyUserRepository(UserRepository):
    def add(self, user: User) -> None:
        with session_scope() as session:
            session.add(
                UserModel(
                    id=user.id,
                    username=user.username,
                    password_hash=user.password_hash,
                    role=user.role.value,
                    is_active=user.is_active,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    last_login_at=user.last_login_at,
                )
            )

    def update(self, user: User) -> None:
        with session_scope() as session:
            row = session.query(UserModel).filter(UserModel.id == user.id).first()
            if not row:
                self.add(user)
                return
            row.username = user.username
            row.password_hash = user.password_hash
            row.role = user.role.value
            row.is_active = user.is_active
            row.updated_at = datetime.utcnow()
            row.last_login_at = user.last_login_at

    def get_by_username(self, username: str) -> User | None:
        with session_scope() as session:
            row = session.query(UserModel).filter(UserModel.username == username).first()
            return _to_user_entity(row) if row else None

    def get_by_id(self, user_id: str) -> User | None:
        with session_scope() as session:
            row = session.query(UserModel).filter(UserModel.id == user_id).first()
            return _to_user_entity(row) if row else None


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def add(self, entry: AuditLogEntry) -> None:
        with session_scope() as session:
            session.add(
                AuditLog(
                    id=entry.id,
                    event_type=entry.event_type,
                    actor_user_id=entry.actor_user_id,
                    task_id=entry.task_id,
                    payload=entry.payload,
                    created_at=entry.created_at,
                )
            )


class SqlAlchemySettingsRepository(SettingsRepository):
    def get_all(self) -> dict[str, Any]:
        with session_scope() as session:
            rows = session.query(Setting).order_by(Setting.key.asc()).all()
            return {row.key: row.value for row in rows}

    def set_many(self, values: dict[str, Any]) -> dict[str, Any]:
        with session_scope() as session:
            for key, value in values.items():
                row = session.query(Setting).filter(Setting.key == key).first()
                if not row:
                    row = Setting(key=key, value=value)
                    session.add(row)
                else:
                    row.value = value
                    row.updated_at = datetime.utcnow()
        return values


def _to_outbox_entity(model: OutboxEntryModel) -> OutboxEntry:
    return OutboxEntry(
        id=model.id,
        event_type=model.event_type,
        aggregate_id=model.aggregate_id,
        payload=model.payload,
        status=model.status,
        created_at=model.created_at,
        published_at=model.published_at,
        retry_count=model.retry_count or 0,
    )


class SqlAlchemyOutboxRepository(OutboxRepository):
    def add(self, entry: OutboxEntry) -> None:
        with session_scope() as session:
            session.add(
                OutboxEntryModel(
                    id=entry.id,
                    event_type=entry.event_type,
                    aggregate_id=entry.aggregate_id,
                    payload=entry.payload,
                    status=entry.status,
                    created_at=entry.created_at,
                    published_at=entry.published_at,
                    retry_count=entry.retry_count,
                )
            )

    def get_pending(self, limit: int = 100) -> list[OutboxEntry]:
        with session_scope() as session:
            try:
                rows = (
                    session.query(OutboxEntryModel)
                    .filter(OutboxEntryModel.status == "pending")
                    .with_for_update(skip_locked=True)
                    .limit(limit)
                    .all()
                )
            except Exception:
                rows = (
                    session.query(OutboxEntryModel)
                    .filter(OutboxEntryModel.status == "pending")
                    .limit(limit)
                    .all()
                )
            return [_to_outbox_entity(row) for row in rows]

    def mark_published(self, entry_id: str) -> None:
        with session_scope() as session:
            row = session.query(OutboxEntryModel).filter(OutboxEntryModel.id == entry_id).first()
            if row:
                row.status = "published"
                row.published_at = datetime.utcnow()

    def mark_failed(self, entry_id: str) -> None:
        with session_scope() as session:
            row = session.query(OutboxEntryModel).filter(OutboxEntryModel.id == entry_id).first()
            if row:
                row.status = "failed"
                row.retry_count = (row.retry_count or 0) + 1
