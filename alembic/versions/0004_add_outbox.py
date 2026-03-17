"""add outbox_entries table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-13 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_outbox_entries_status", "outbox_entries", ["status"])
    op.create_index("ix_outbox_entries_aggregate_id", "outbox_entries", ["aggregate_id"])


def downgrade() -> None:
    op.drop_index("ix_outbox_entries_aggregate_id", table_name="outbox_entries")
    op.drop_index("ix_outbox_entries_status", table_name="outbox_entries")
    op.drop_table("outbox_entries")
