"""add web login tickets

Revision ID: 6f7a8b9c0d12
Revises: 5d8a6c1f2b34
Create Date: 2026-03-23 23:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f7a8b9c0d12"
down_revision: Union[str, Sequence[str], None] = "5d8a6c1f2b34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "web_login_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket"),
    )
    op.create_index(op.f("ix_web_login_tickets_id"), "web_login_tickets", ["id"], unique=False)
    op.create_index(op.f("ix_web_login_tickets_ticket"), "web_login_tickets", ["ticket"], unique=False)
    op.create_index(op.f("ix_web_login_tickets_status"), "web_login_tickets", ["status"], unique=False)
    op.create_index(op.f("ix_web_login_tickets_expires_at"), "web_login_tickets", ["expires_at"], unique=False)
    op.create_index(op.f("ix_web_login_tickets_user_id"), "web_login_tickets", ["user_id"], unique=False)
    op.create_index(op.f("ix_web_login_tickets_tenant_id"), "web_login_tickets", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_web_login_tickets_tenant_id"), table_name="web_login_tickets")
    op.drop_index(op.f("ix_web_login_tickets_user_id"), table_name="web_login_tickets")
    op.drop_index(op.f("ix_web_login_tickets_expires_at"), table_name="web_login_tickets")
    op.drop_index(op.f("ix_web_login_tickets_status"), table_name="web_login_tickets")
    op.drop_index(op.f("ix_web_login_tickets_ticket"), table_name="web_login_tickets")
    op.drop_index(op.f("ix_web_login_tickets_id"), table_name="web_login_tickets")
    op.drop_table("web_login_tickets")
