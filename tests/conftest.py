"""
Shared pytest fixtures for the Article Summarizer test suite.

DB integration fixtures use pytest-postgresql to provision a temporary
PostgreSQL instance — they are only used by tests/test_db_integration.py.
The regular unit tests do not depend on PostgreSQL at all.
"""
from __future__ import annotations

import pytest


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

        from models import Base

        conn = postgresql
        db_url = (
            f"postgresql+psycopg2://{conn.info.user}:{conn.info.password or ''}"
            f"@{conn.info.host}:{conn.info.port}/{conn.info.dbname}"
        )
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

except ImportError:
    # pytest-postgresql not installed — DB integration tests will be skipped
    pass
