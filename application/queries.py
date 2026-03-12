"""Query DTOs for read operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GetTaskStatusQuery:
    task_id: str


@dataclass(slots=True)
class GetTaskDownloadQuery:
    task_id: str
    fmt: str


@dataclass(slots=True)
class ListTaskHistoryQuery:
    page: int = 1
    per_page: int = 20


@dataclass(slots=True)
class GetTaskStatisticsQuery:
    pass


@dataclass(slots=True)
class GetSystemStatusQuery:
    pass


@dataclass(slots=True)
class GetSettingsQuery:
    pass
