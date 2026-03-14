"""add invites table

Revision ID: d0bcc097e20f
Revises: 9969606c99a3
Create Date: 2026-03-15 04:52:20.513815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0bcc097e20f'
down_revision: Union[str, Sequence[str], None] = '9969606c99a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], name=op.f("fk_invites_invited_by_user_id_users")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_invites_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invites")),
        sa.UniqueConstraint("token", name=op.f("uq_invites_token")),
    )
    op.create_index(op.f("ix_invites_id"), "invites", ["id"], unique=False)
    op.create_index(op.f("ix_invites_invited_by_user_id"), "invites", ["invited_by_user_id"], unique=False)
    op.create_index(op.f("ix_invites_status"), "invites", ["status"], unique=False)
    op.create_index(op.f("ix_invites_tenant_id"), "invites", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_invites_token"), "invites", ["token"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_invites_token"), table_name="invites")
    op.drop_index(op.f("ix_invites_tenant_id"), table_name="invites")
    op.drop_index(op.f("ix_invites_status"), table_name="invites")
    op.drop_index(op.f("ix_invites_invited_by_user_id"), table_name="invites")
    op.drop_index(op.f("ix_invites_id"), table_name="invites")
    op.drop_table("invites")
