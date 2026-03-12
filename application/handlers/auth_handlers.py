"""Authentication and authorisation handlers."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from application.commands import AuthenticateUserCommand
from application.event_bus import EventBus
from application.ports import PasswordVerifier
from domain.entities import AuditLogEntry
from domain.events import UserAuthenticated
from domain.repositories import AuditLogRepository, UserRepository


class AuthenticateUserHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        password_verifier: PasswordVerifier,
        audit_repository: AuditLogRepository,
        event_bus: EventBus,
    ) -> None:
        self._user_repository = user_repository
        self._password_verifier = password_verifier
        self._audit_repository = audit_repository
        self._event_bus = event_bus

    def handle(self, command: AuthenticateUserCommand):
        user = self._user_repository.get_by_username(command.username)
        if not user or not user.is_active:
            return None
        if not self._password_verifier.verify_password(command.password, user.password_hash):
            return None

        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self._user_repository.update(user)

        entry = AuditLogEntry(
            id=str(uuid4()),
            event_type="UserAuthenticated",
            actor_user_id=user.id,
            task_id=None,
            payload={"username": user.username, "role": user.role.value},
        )
        self._audit_repository.add(entry)
        self._event_bus.publish(
            UserAuthenticated(
                aggregate_id=user.id,
                payload={"username": user.username, "role": user.role.value},
            )
        )
        return user
