"""Domain layer for the Article Summarizer application."""

from .entities import (
    AuditLogEntry,
    SettingsEntry,
    SummarizationTask,
    TaskStatus,
    User,
    UserRole,
)
from .events import (
    CacheCleared,
    DomainEvent,
    JwtSecretRotated,
    TaskCompleted,
    TaskFailed,
    TaskSubmitted,
    UserAuthenticated,
)

__all__ = [
    "AuditLogEntry",
    "CacheCleared",
    "DomainEvent",
    "JwtSecretRotated",
    "SettingsEntry",
    "SummarizationTask",
    "TaskCompleted",
    "TaskFailed",
    "TaskStatus",
    "TaskSubmitted",
    "User",
    "UserAuthenticated",
    "UserRole",
]
