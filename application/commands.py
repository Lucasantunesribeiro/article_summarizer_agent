"""Command DTOs for write operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SubmitSummarizationCommand:
    url: str
    method: str
    length: str
    client_ip: str


@dataclass(slots=True)
class CompleteTaskCommand:
    task_id: str
    result: dict[str, Any]


@dataclass(slots=True)
class FailTaskCommand:
    task_id: str
    error: str


@dataclass(slots=True)
class AuthenticateUserCommand:
    username: str
    password: str


@dataclass(slots=True)
class ClearCacheCommand:
    actor_user_id: str | None
    actor_username: str | None


@dataclass(slots=True)
class RotateJwtSecretCommand:
    actor_user_id: str | None
    actor_username: str | None
    new_secret: str | None = None
    grace_period_seconds: int = 3600


@dataclass(slots=True)
class UpdateSettingsCommand:
    actor_user_id: str | None
    actor_username: str | None
    values: dict[str, Any] = field(default_factory=dict)
