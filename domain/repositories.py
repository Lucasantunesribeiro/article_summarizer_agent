"""Repository contracts used by the application layer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .entities import AuditLogEntry, SummarizationTask, User


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: SummarizationTask) -> None: ...

    @abstractmethod
    def update(self, task: SummarizationTask) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> SummarizationTask | None: ...

    @abstractmethod
    def list_recent(
        self, page: int = 1, per_page: int = 20, statuses: tuple[str, ...] | None = None
    ) -> tuple[list[SummarizationTask], int]: ...

    @abstractmethod
    def get_statistics(self) -> dict[str, int]: ...


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None: ...

    @abstractmethod
    def update(self, user: User) -> None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None: ...


class AuditLogRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditLogEntry) -> None: ...


class SettingsRepository(ABC):
    @abstractmethod
    def get_all(self) -> dict[str, Any]: ...

    @abstractmethod
    def set_many(self, values: dict[str, Any]) -> dict[str, Any]: ...
