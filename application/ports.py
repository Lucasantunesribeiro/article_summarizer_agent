"""Application-layer service contracts."""
from __future__ import annotations

from typing import Any, Protocol

from domain.entities import User


class PipelineRunner(Protocol):
    def run(self, url: str, method: str | None = None, length: str | None = None) -> dict[str, Any]:
        ...

    def get_status(self) -> dict[str, Any]: ...

    def clear_cache(self) -> None: ...


class TaskDispatcher(Protocol):
    def dispatch(self, task_id: str, url: str, method: str, length: str) -> None: ...


class PasswordVerifier(Protocol):
    def hash_password(self, raw_password: str) -> str: ...

    def verify_password(self, raw_password: str, password_hash: str) -> bool: ...


class UserContext(Protocol):
    user: User | None
