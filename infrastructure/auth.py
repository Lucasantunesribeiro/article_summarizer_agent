"""Authentication-related infrastructure services."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from domain.entities import User, UserRole
from domain.repositories import UserRepository


class PasswordService:
    def hash_password(self, raw_password: str) -> str:
        return generate_password_hash(raw_password)

    def verify_password(self, raw_password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, raw_password)


class AdminBootstrapper:
    def __init__(self, user_repository: UserRepository, password_service: PasswordService) -> None:
        self._user_repository = user_repository
        self._password_service = password_service

    def ensure_admin(self, username: str, password: str) -> User | None:
        if not username or not password:
            return None

        existing = self._user_repository.get_by_username(username)
        if existing:
            return existing

        user = User(
            id=str(uuid4()),
            username=username,
            password_hash=self._password_service.hash_password(password),
            role=UserRole.ADMIN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._user_repository.add(user)
        return user
