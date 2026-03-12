"""Domain events for business-relevant actions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class DomainEvent:
    aggregate_id: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(slots=True)
class TaskSubmitted(DomainEvent):
    pass


@dataclass(slots=True)
class TaskCompleted(DomainEvent):
    pass


@dataclass(slots=True)
class TaskFailed(DomainEvent):
    pass


@dataclass(slots=True)
class UserAuthenticated(DomainEvent):
    pass


@dataclass(slots=True)
class CacheCleared(DomainEvent):
    pass


@dataclass(slots=True)
class JwtSecretRotated(DomainEvent):
    pass
