"""Core domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    ERROR = "error"


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass(slots=True)
class SummarizationTask:
    id: str
    url: str
    method: str
    length: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: int = 0
    message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    summary: str | None = None
    error: str | None = None
    statistics: dict[str, Any] | None = None
    files_created: dict[str, Any] | None = None
    method_used: str | None = None
    execution_time: float | None = None
    idempotency_key: str | None = None

    def mark_processing(self) -> None:
        self.status = TaskStatus.PROCESSING
        self.progress = 10
        self.message = "Extracting article content..."

    def mark_completed(self, result: dict[str, Any]) -> None:
        self.status = TaskStatus.DONE
        self.progress = 100
        self.message = "Done!"
        self.summary = result.get("summary")
        self.statistics = result.get("statistics")
        self.files_created = result.get("files_created")
        self.method_used = result.get("method_used")
        self.execution_time = result.get("execution_time")
        self.finished_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.progress = 0
        self.message = error
        self.error = error
        self.finished_at = datetime.utcnow()


@dataclass(slots=True)
class User:
    id: str
    username: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: datetime | None = None

    def can_manage_system(self) -> bool:
        return self.is_active and self.role == UserRole.ADMIN


@dataclass(slots=True)
class AuditLogEntry:
    id: str
    event_type: str
    actor_user_id: str | None
    task_id: str | None
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class SettingsEntry:
    key: str
    value: Any
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class OutboxEntry:
    id: str
    event_type: str
    aggregate_id: str
    payload: dict[str, Any]
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    retry_count: int = 0
