"""add dead_letter_entries table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-13 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dead_letter_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("exception", sa.Text, nullable=True),
        sa.Column("traceback", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_dead_letter_entries_task_id", "dead_letter_entries", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_dead_letter_entries_task_id", table_name="dead_letter_entries")
    op.drop_table("dead_letter_entries")
