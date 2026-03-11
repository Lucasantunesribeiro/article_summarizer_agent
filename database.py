"""Database session factory with SQLite fallback for dev."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# psycopg2 uses 'postgresql://' but SQLAlchemy prefers 'postgresql+psycopg2://'
# Render/Heroku provide 'postgres://' — fix it
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    # SQLite doesn't support pool_size/max_overflow
    **({} if DATABASE_URL.startswith("sqlite") else {"pool_size": 5, "max_overflow": 10}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables (idempotent — safe to call on startup)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Generator for DB session dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
