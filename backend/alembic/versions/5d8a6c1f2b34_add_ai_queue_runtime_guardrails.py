"""add ai queue runtime guardrails

Revision ID: 5d8a6c1f2b34
Revises: e4f5a6b7c8d9
Create Date: 2026-03-23 16:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d8a6c1f2b34"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_tasks", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_tasks", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_tasks", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_tasks", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_tasks", sa.Column("worker_id", sa.String(length=128), nullable=True))

    op.create_index(op.f("ix_ai_tasks_next_retry_at"), "ai_tasks", ["next_retry_at"], unique=False)
    op.create_index(op.f("ix_ai_tasks_heartbeat_at"), "ai_tasks", ["heartbeat_at"], unique=False)
    op.create_index(op.f("ix_ai_tasks_worker_id"), "ai_tasks", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_tasks_worker_id"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_heartbeat_at"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_next_retry_at"), table_name="ai_tasks")

    op.drop_column("ai_tasks", "worker_id")
    op.drop_column("ai_tasks", "heartbeat_at")
    op.drop_column("ai_tasks", "claimed_at")
    op.drop_column("ai_tasks", "next_retry_at")
    op.drop_column("ai_tasks", "retry_count")
