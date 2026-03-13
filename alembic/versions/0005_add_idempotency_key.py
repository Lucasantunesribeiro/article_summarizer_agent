"""add idempotency_key to tasks

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-13 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(64), nullable=True))
        batch_op.create_unique_constraint("uq_tasks_idempotency_key", ["idempotency_key"])
        batch_op.create_index("ix_tasks_idempotency_key", ["idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_idempotency_key")
        batch_op.drop_constraint("uq_tasks_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
