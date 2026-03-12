"""create tasks table

Revision ID: 0001
Revises:
Create Date: 2026-03-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("method", sa.String(20), nullable=True),
        sa.Column("length", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("statistics", sa.JSON, nullable=True),
        sa.Column("files_created", sa.JSON, nullable=True),
        sa.Column("method_used", sa.String(30), nullable=True),
        sa.Column("execution_time", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tasks")
