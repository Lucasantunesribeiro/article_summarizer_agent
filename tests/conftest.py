"""Shared pytest fixtures for the Article Summarizer test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.config import Config as AlembicConfig
from flask_jwt_extended import create_access_token

from alembic import command

ROOT = Path(__file__).resolve().parents[1]
TEST_DB_PATH = ROOT / "test_app.sqlite3"

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-thirty-two-characters")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("FLASK_DEBUG", "true")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "Admin123!")
os.environ.setdefault("JWT_COOKIE_CSRF_PROTECT", "true")
os.environ.setdefault("REDIS_URL", "")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"


def _run_migrations(database_url: str) -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    alembic_cfg = AlembicConfig(str(ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


_run_migrations(os.environ["DATABASE_URL"])


def _reset_database() -> None:
    from database import session_scope
    from models import AuditLog, Setting, Task, User

    with session_scope() as session:
        session.query(AuditLog).delete()
        session.query(Setting).delete()
        session.query(User).delete()
        session.query(Task).delete()


@pytest.fixture
def app_instance(monkeypatch):
    from infrastructure.container import build_runtime_container
    from presentation.app_factory import create_app

    _reset_database()
    build_runtime_container.cache_clear()

    app = create_app()
    app.config["TESTING"] = True
    monkeypatch.setattr(
        app.extensions["container"].submit_task_handler._event_bus, "publish", lambda event: None
    )

    yield app

    build_runtime_container.cache_clear()


@pytest.fixture
def client(app_instance):
    with app_instance.test_client() as test_client:
        yield test_client


@pytest.fixture
def container(app_instance):
    return app_instance.extensions["container"]


@pytest.fixture
def admin_user(container):
    return container.user_repository.get_by_username(os.environ["ADMIN_USER"])


@pytest.fixture
def admin_headers(app_instance, admin_user):
    with app_instance.app_context():
        token = create_access_token(
            identity=admin_user.id,
            additional_claims={"role": admin_user.role.value, "username": admin_user.username},
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(app_instance, container):
    from domain.entities import User, UserRole

    viewer = User(
        id="viewer-user-id",
        username="viewer",
        password_hash=container.password_service.hash_password("Viewer123!"),
        role=UserRole.VIEWER,
    )
    container.user_repository.add(viewer)

    with app_instance.app_context():
        token = create_access_token(
            identity=viewer.id,
            additional_claims={"role": viewer.role.value, "username": viewer.username},
        )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# PostgreSQL fixtures (only active when pytest-postgresql is installed)
# ---------------------------------------------------------------------------

try:
    from pytest_postgresql import factories as pg_factories

    postgresql_proc = pg_factories.postgresql_proc(port=None)
    postgresql = pg_factories.postgresql("postgresql_proc")

    @pytest.fixture
    def db_session(postgresql):
        """SQLAlchemy session backed by a real, temporary PostgreSQL DB."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        conn = postgresql
        db_url = (
            f"postgresql+psycopg2://{conn.info.user}:{conn.info.password or ''}"
            f"@{conn.info.host}:{conn.info.port}/{conn.info.dbname}"
        )
        alembic_cfg = AlembicConfig(str(ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        previous_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = db_url
        try:
            command.upgrade(alembic_cfg, "head")
        finally:
            if previous_db_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_db_url

        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
        engine.dispose()

except ImportError:
    pass
