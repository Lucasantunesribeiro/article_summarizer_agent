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
    op.add_column("tasks", sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_tasks_idempotency_key", "tasks", ["idempotency_key"])
    op.create_index("ix_tasks_idempotency_key", "tasks", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_tasks_idempotency_key", table_name="tasks")
    op.drop_constraint("uq_tasks_idempotency_key", "tasks", type_="unique")
    op.drop_column("tasks", "idempotency_key")
