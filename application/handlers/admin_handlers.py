"""Administrative handlers."""
from __future__ import annotations

from uuid import uuid4

from application.commands import ClearCacheCommand, RotateJwtSecretCommand, UpdateSettingsCommand
from application.event_bus import EventBus
from application.ports import PipelineRunner
from application.queries import GetSettingsQuery
from domain.entities import AuditLogEntry
from domain.events import CacheCleared, JwtSecretRotated
from domain.repositories import AuditLogRepository, SettingsRepository


class ClearCacheHandler:
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        audit_repository: AuditLogRepository,
        event_bus: EventBus,
    ) -> None:
        self._pipeline_runner = pipeline_runner
        self._audit_repository = audit_repository
        self._event_bus = event_bus

    def handle(self, command: ClearCacheCommand) -> dict:
        self._pipeline_runner.clear_cache()
        self._audit_repository.add(
            AuditLogEntry(
                id=str(uuid4()),
                event_type="CacheCleared",
                actor_user_id=command.actor_user_id,
                task_id=None,
                payload={"actor_username": command.actor_username},
            )
        )
        self._event_bus.publish(
            CacheCleared(
                aggregate_id=command.actor_user_id or "anonymous",
                payload={"actor_username": command.actor_username},
            )
        )
        return {"success": True, "message": "Cache cleared."}


class RotateJwtSecretHandler:
    def __init__(
        self,
        secrets_manager,
        audit_repository: AuditLogRepository,
        event_bus: EventBus,
    ) -> None:
        self._secrets_manager = secrets_manager
        self._audit_repository = audit_repository
        self._event_bus = event_bus

    def handle(self, command: RotateJwtSecretCommand) -> dict:
        result = self._secrets_manager.rotate(
            new_secret=command.new_secret,
            grace_period_seconds=command.grace_period_seconds,
        )
        self._audit_repository.add(
            AuditLogEntry(
                id=str(uuid4()),
                event_type="JwtSecretRotated",
                actor_user_id=command.actor_user_id,
                task_id=None,
                payload={
                    "actor_username": command.actor_username,
                    "grace_period_seconds": command.grace_period_seconds,
                },
            )
        )
        self._event_bus.publish(
            JwtSecretRotated(
                aggregate_id=command.actor_user_id or "anonymous",
                payload=result,
            )
        )
        return {"success": True, **result}


class GetSettingsHandler:
    def __init__(self, settings_repository: SettingsRepository) -> None:
        self._settings_repository = settings_repository

    def handle(self, query: GetSettingsQuery) -> dict:
        return self._settings_repository.get_all()


class UpdateSettingsHandler:
    def __init__(
        self,
        settings_repository: SettingsRepository,
        audit_repository: AuditLogRepository,
        settings_applier=None,
    ) -> None:
        self._settings_repository = settings_repository
        self._audit_repository = audit_repository
        self._settings_applier = settings_applier

    def handle(self, command: UpdateSettingsCommand) -> dict:
        saved = self._settings_repository.set_many(command.values)
        if self._settings_applier:
            self._settings_applier.apply(saved)
        self._audit_repository.add(
            AuditLogEntry(
                id=str(uuid4()),
                event_type="SettingsUpdated",
                actor_user_id=command.actor_user_id,
                task_id=None,
                payload={"actor_username": command.actor_username, "keys": sorted(saved)},
            )
        )
        return saved
