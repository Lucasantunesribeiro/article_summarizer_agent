"""Command/query handlers related to summarization tasks."""

from __future__ import annotations

from dataclasses import asdict
from math import ceil
from uuid import uuid4

from application.commands import CompleteTaskCommand, FailTaskCommand, SubmitSummarizationCommand
from application.event_bus import EventBus
from application.ports import PipelineRunner
from application.queries import (
    GetSystemStatusQuery,
    GetTaskDownloadQuery,
    GetTaskStatisticsQuery,
    GetTaskStatusQuery,
    ListTaskHistoryQuery,
)
from domain.entities import SummarizationTask
from domain.events import TaskCompleted, TaskFailed, TaskSubmitted
from domain.repositories import SettingsRepository, TaskRepository


def serialize_task(task: SummarizationTask) -> dict:
    data = asdict(task)
    data["status"] = task.status.value
    data["created_at"] = task.created_at.isoformat()
    data["finished_at"] = task.finished_at.isoformat() if task.finished_at else None
    if task.status.value == "done":
        data["result"] = {
            "summary": task.summary or "",
            "statistics": task.statistics or {},
            "method_used": task.method_used or "",
            "execution_time": task.execution_time or 0,
            "files_created": task.files_created or {},
        }
    return data


class SubmitSummarizationHandler:
    def __init__(
        self,
        task_repository: TaskRepository,
        event_bus: EventBus,
    ) -> None:
        self._task_repository = task_repository
        self._event_bus = event_bus

    def handle(self, command: SubmitSummarizationCommand) -> SummarizationTask:
        task = SummarizationTask(
            id=str(uuid4()),
            url=command.url,
            method=command.method,
            length=command.length,
            message="Queued...",
        )
        self._task_repository.add(task)
        self._event_bus.publish(
            TaskSubmitted(
                aggregate_id=task.id,
                payload={
                    "task_id": task.id,
                    "url": task.url,
                    "method": task.method,
                    "length": task.length,
                    "client_ip": command.client_ip,
                },
            )
        )
        return task


class ProcessTaskHandler:
    def __init__(
        self,
        task_repository: TaskRepository,
        pipeline_runner: PipelineRunner,
        event_bus: EventBus,
    ) -> None:
        self._task_repository = task_repository
        self._pipeline_runner = pipeline_runner
        self._event_bus = event_bus

    def handle(self, task_id: str, url: str, method: str, length: str) -> dict:
        try:
            from modules.metrics import ACTIVE_TASKS

            ACTIVE_TASKS.inc()
        except Exception:
            pass
        task = self._task_repository.get(task_id)
        if not task:
            try:
                from modules.metrics import ACTIVE_TASKS

                ACTIVE_TASKS.dec()
            except Exception:
                pass
            raise ValueError(f"Task {task_id} not found.")

        task.mark_processing()
        self._task_repository.update(task)
        try:
            result = self._pipeline_runner.run(url, method=method, length=length)
            if result.get("success"):
                completed = CompleteTaskCommand(task_id=task_id, result=result)
                return CompleteTaskHandler(self._task_repository, self._event_bus).handle(completed)

            failure = FailTaskCommand(task_id=task_id, error=result.get("error", "Unknown error"))
            return FailTaskHandler(self._task_repository, self._event_bus).handle(failure)
        except Exception as exc:
            failure = FailTaskCommand(task_id=task_id, error=str(exc))
            return FailTaskHandler(self._task_repository, self._event_bus).handle(failure)
        finally:
            try:
                from modules.metrics import ACTIVE_TASKS

                ACTIVE_TASKS.dec()
            except Exception:
                pass


class CompleteTaskHandler:
    def __init__(self, task_repository: TaskRepository, event_bus: EventBus) -> None:
        self._task_repository = task_repository
        self._event_bus = event_bus

    def handle(self, command: CompleteTaskCommand) -> dict:
        task = self._task_repository.get(command.task_id)
        if not task:
            raise ValueError(f"Task {command.task_id} not found.")
        task.mark_completed(command.result)
        self._task_repository.update(task)
        try:
            from modules.metrics import SUMMARIZATION_DURATION, SUMMARIZATION_REQUESTS

            SUMMARIZATION_REQUESTS.labels(
                status="success", method=task.method or "extractive"
            ).inc()
            if task.execution_time:
                SUMMARIZATION_DURATION.observe(task.execution_time)
        except Exception:
            pass
        self._event_bus.publish(
            TaskCompleted(
                aggregate_id=task.id,
                payload={
                    "task_id": task.id,
                    "url": task.url,
                    "method_used": task.method_used,
                    "execution_time": task.execution_time,
                },
            )
        )
        return command.result


class FailTaskHandler:
    def __init__(self, task_repository: TaskRepository, event_bus: EventBus) -> None:
        self._task_repository = task_repository
        self._event_bus = event_bus

    def handle(self, command: FailTaskCommand) -> dict:
        task = self._task_repository.get(command.task_id)
        if not task:
            raise ValueError(f"Task {command.task_id} not found.")
        task.mark_failed(command.error)
        self._task_repository.update(task)
        try:
            from modules.metrics import SUMMARIZATION_REQUESTS

            SUMMARIZATION_REQUESTS.labels(
                status="failure", method=task.method or "extractive"
            ).inc()
        except Exception:
            pass
        self._event_bus.publish(
            TaskFailed(
                aggregate_id=task.id,
                payload={"task_id": task.id, "url": task.url, "error": command.error},
            )
        )
        return {"success": False, "error": command.error}


class GetTaskStatusHandler:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    def handle(self, query: GetTaskStatusQuery) -> dict | None:
        task = self._task_repository.get(query.task_id)
        return serialize_task(task) if task else None


class GetTaskDownloadHandler:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    def handle(self, query: GetTaskDownloadQuery) -> str | None:
        task = self._task_repository.get(query.task_id)
        if not task or not task.files_created:
            return None
        path = task.files_created.get(query.fmt)
        return str(path) if path else None


class ListTaskHistoryHandler:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    def handle(self, query: ListTaskHistoryQuery) -> dict:
        tasks, total = self._task_repository.list_recent(
            page=query.page,
            per_page=query.per_page,
            statuses=("done", "failed", "error"),
        )
        total_pages = max(1, ceil(total / query.per_page)) if query.per_page else 1
        return {
            "tasks": [serialize_task(task) for task in tasks],
            "page": query.page,
            "per_page": query.per_page,
            "total": total,
            "total_pages": total_pages,
        }


class GetTaskStatisticsHandler:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    def handle(self, query: GetTaskStatisticsQuery) -> dict:
        return self._task_repository.get_statistics()


class GetSystemStatusHandler:
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        settings_repository: SettingsRepository,
    ) -> None:
        self._pipeline_runner = pipeline_runner
        self._settings_repository = settings_repository

    def handle(self, query: GetSystemStatusQuery) -> dict:
        status = self._pipeline_runner.get_status()
        status["settings_overrides"] = self._settings_repository.get_all()
        return status
