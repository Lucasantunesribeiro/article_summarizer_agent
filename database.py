"""Database session factory utilities."""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from threading import Lock

from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

ENGINE_OPTIONS: dict[str, object] = {"pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    ENGINE_OPTIONS.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(DATABASE_URL, **ENGINE_OPTIONS)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_migration_lock = Lock()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Validate database connectivity without mutating the schema."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@lru_cache(maxsize=1)
def upgrade_schema() -> None:
    """Apply Alembic migrations once per process before the app starts serving."""
    if os.getenv("SKIP_DB_MIGRATIONS_ON_STARTUP", "").lower() == "true":
        return

    with _migration_lock:
        project_root = Path(__file__).resolve().parent
        alembic_cfg = AlembicConfig(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        engine.dispose()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
