"""Dependency container and runtime wiring."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import uuid4

from application.event_bus import EventBus
from application.handlers.admin_handlers import (
    ClearCacheHandler,
    GetSettingsHandler,
    RotateJwtSecretHandler,
    UpdateSettingsHandler,
)
from application.handlers.auth_handlers import AuthenticateUserHandler
from application.handlers.task_handlers import (
    GetSystemStatusHandler,
    GetTaskDownloadHandler,
    GetTaskStatisticsHandler,
    GetTaskStatusHandler,
    ListTaskHistoryHandler,
    ProcessTaskHandler,
    SubmitSummarizationHandler,
)
from config import config
from domain.entities import AuditLogEntry
from domain.events import TaskCompleted, TaskFailed, TaskSubmitted
from infrastructure.auth import AdminBootstrapper, PasswordService
from infrastructure.pipeline import ArticlePipelineRunner
from infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemySettingsRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyUserRepository,
)
from infrastructure.runtime_settings import RuntimeSettingsApplier
from modules.cache import create_cache_backend
from modules.rate_limiter import create_rate_limiter
from modules.secrets_manager import secrets_manager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RuntimeContainer:
    pipeline_runner: ArticlePipelineRunner
    submit_task_handler: SubmitSummarizationHandler
    process_task_handler: ProcessTaskHandler
    get_task_status_handler: GetTaskStatusHandler
    get_task_download_handler: GetTaskDownloadHandler
    list_task_history_handler: ListTaskHistoryHandler
    get_task_statistics_handler: GetTaskStatisticsHandler
    get_system_status_handler: GetSystemStatusHandler
    authenticate_user_handler: AuthenticateUserHandler
    clear_cache_handler: ClearCacheHandler
    rotate_jwt_secret_handler: RotateJwtSecretHandler
    get_settings_handler: GetSettingsHandler
    update_settings_handler: UpdateSettingsHandler
    task_repository: SqlAlchemyTaskRepository
    user_repository: SqlAlchemyUserRepository
    audit_repository: SqlAlchemyAuditLogRepository
    settings_repository: SqlAlchemySettingsRepository
    password_service: PasswordService
    rate_limiters: dict[str, Any]
    secrets_manager: Any


class AsyncTaskDispatcher:
    def __init__(self, process_task_handler: ProcessTaskHandler) -> None:
        self._process_task_handler = process_task_handler
        self._celery_available = False
        try:
            from celery_app import celery as celery_app  # noqa: PLC0415

            celery_app.control.inspect(timeout=1.0).ping()
            self._celery_available = True
        except Exception as exc:
            logger.warning("Celery not available (%s) — using thread dispatcher.", exc)

    def dispatch(self, task_id: str, url: str, method: str, length: str) -> None:
        if self._celery_available:
            from tasks.summarization_task import summarize_article  # noqa: PLC0415

            summarize_article.delay(task_id, url, method, length)
            return

        thread = threading.Thread(
            target=self._process_task_handler.handle,
            args=(task_id, url, method, length),
            daemon=True,
        )
        thread.start()


def _build_rate_limiters() -> dict[str, Any]:
    return {
        "submit": create_rate_limiter(
            max_requests=config.rate_limit.max_requests,
            window_seconds=config.rate_limit.window_seconds,
        ),
        "auth": create_rate_limiter(
            max_requests=config.rate_limit.auth_max_requests,
            window_seconds=config.rate_limit.auth_window_seconds,
        ),
        "polling": create_rate_limiter(
            max_requests=config.rate_limit.polling_max_requests,
            window_seconds=config.rate_limit.polling_window_seconds,
        ),
        "admin": create_rate_limiter(
            max_requests=config.rate_limit.admin_max_requests,
            window_seconds=config.rate_limit.admin_window_seconds,
        ),
    }


def _build_default_settings() -> dict[str, Any]:
    return {
        "scraping.timeout": config.scraping.timeout,
        "scraping.max_retries": config.scraping.max_retries,
        "scraping.max_content_bytes": config.scraping.max_content_bytes,
        "summarization.default_method": config.summarization.method,
        "summarization.default_length": config.summarization.summary_length,
        "summarization.gemini_model_id": config.gemini.model_id,
        "output.cache_enabled": config.output.cache_enabled,
        "output.cache_ttl": config.output.cache_ttl,
        "rate_limit.submit.max_requests": config.rate_limit.max_requests,
        "rate_limit.submit.window_seconds": config.rate_limit.window_seconds,
        "rate_limit.auth.max_requests": config.rate_limit.auth_max_requests,
        "rate_limit.auth.window_seconds": config.rate_limit.auth_window_seconds,
        "rate_limit.polling.max_requests": config.rate_limit.polling_max_requests,
        "rate_limit.polling.window_seconds": config.rate_limit.polling_window_seconds,
        "rate_limit.admin.max_requests": config.rate_limit.admin_max_requests,
        "rate_limit.admin.window_seconds": config.rate_limit.admin_window_seconds,
    }


@lru_cache(maxsize=1)
def build_runtime_container() -> RuntimeContainer:
    event_bus = EventBus()
    cache_backend = create_cache_backend(ttl=config.output.cache_ttl)
    pipeline_runner = ArticlePipelineRunner(cache_backend=cache_backend)

    task_repository = SqlAlchemyTaskRepository()
    user_repository = SqlAlchemyUserRepository()
    audit_repository = SqlAlchemyAuditLogRepository()
    settings_repository = SqlAlchemySettingsRepository()
    password_service = PasswordService()
    rate_limiters = _build_rate_limiters()
    settings_applier = RuntimeSettingsApplier(pipeline_runner, rate_limiters)

    bootstrapper = AdminBootstrapper(user_repository, password_service)
    bootstrapper.ensure_admin(config.auth.seed_admin_username, config.auth.seed_admin_password)

    if not settings_repository.get_all():
        settings_repository.set_many(_build_default_settings())
    settings_applier.apply(settings_repository.get_all())

    submit_task_handler = SubmitSummarizationHandler(task_repository, event_bus)
    process_task_handler = ProcessTaskHandler(task_repository, pipeline_runner, event_bus)
    dispatcher = AsyncTaskDispatcher(process_task_handler)

    event_bus.subscribe(
        TaskSubmitted,
        lambda event: dispatcher.dispatch(
            task_id=event.payload["task_id"],
            url=event.payload["url"],
            method=event.payload["method"],
            length=event.payload["length"],
        ),
    )

    def _record_task_event(event) -> None:
        audit_repository.add(
            AuditLogEntry(
                id=str(uuid4()),
                event_type=event.event_type,
                actor_user_id=None,
                task_id=event.payload.get("task_id"),
                payload=event.payload,
            )
        )

    event_bus.subscribe(TaskCompleted, _record_task_event)
    event_bus.subscribe(TaskFailed, _record_task_event)

    return RuntimeContainer(
        pipeline_runner=pipeline_runner,
        submit_task_handler=submit_task_handler,
        process_task_handler=process_task_handler,
        get_task_status_handler=GetTaskStatusHandler(task_repository),
        get_task_download_handler=GetTaskDownloadHandler(task_repository),
        list_task_history_handler=ListTaskHistoryHandler(task_repository),
        get_task_statistics_handler=GetTaskStatisticsHandler(task_repository),
        get_system_status_handler=GetSystemStatusHandler(pipeline_runner, settings_repository),
        authenticate_user_handler=AuthenticateUserHandler(
            user_repository=user_repository,
            password_verifier=password_service,
            audit_repository=audit_repository,
            event_bus=event_bus,
        ),
        clear_cache_handler=ClearCacheHandler(
            pipeline_runner=pipeline_runner,
            audit_repository=audit_repository,
            event_bus=event_bus,
        ),
        rotate_jwt_secret_handler=RotateJwtSecretHandler(
            secrets_manager=secrets_manager,
            audit_repository=audit_repository,
            event_bus=event_bus,
        ),
        get_settings_handler=GetSettingsHandler(settings_repository),
        update_settings_handler=UpdateSettingsHandler(
            settings_repository,
            audit_repository,
            settings_applier=settings_applier,
        ),
        task_repository=task_repository,
        user_repository=user_repository,
        audit_repository=audit_repository,
        settings_repository=settings_repository,
        password_service=password_service,
        rate_limiters=rate_limiters,
        secrets_manager=secrets_manager,
    )
