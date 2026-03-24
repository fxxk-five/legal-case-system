"""add auth sessions and wechat identity fields

Revision ID: e4f5a6b7c8d9
Revises: 2b3c4d5e6f70
Create Date: 2026-03-23 20:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("wechat_unionid", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("wechat_bound_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("wechat_phone_snapshot", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("last_login_channel", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_users_last_login_channel"), "users", ["last_login_channel"], unique=False)
    op.create_index(op.f("ix_users_wechat_unionid"), "users", ["wechat_unionid"], unique=False)
    op.create_unique_constraint(op.f("uq_users_wechat_unionid"), "users", ["wechat_unionid"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=True),
        sa.Column("device_type", sa.String(length=30), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_auth_sessions_refresh_token_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_id"), "auth_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_tenant_id"), "auth_sessions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_refresh_token_hash"), "auth_sessions", ["refresh_token_hash"], unique=False)
    op.create_index(op.f("ix_auth_sessions_expires_at"), "auth_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_auth_sessions_channel"), "auth_sessions", ["channel"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_sessions_channel"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_expires_at"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_refresh_token_hash"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_tenant_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_constraint(op.f("uq_users_wechat_unionid"), "users", type_="unique")
    op.drop_index(op.f("ix_users_wechat_unionid"), table_name="users")
    op.drop_index(op.f("ix_users_last_login_channel"), table_name="users")
    op.drop_column("users", "last_login_channel")
    op.drop_column("users", "wechat_phone_snapshot")
    op.drop_column("users", "wechat_bound_at")
    op.drop_column("users", "wechat_unionid")
