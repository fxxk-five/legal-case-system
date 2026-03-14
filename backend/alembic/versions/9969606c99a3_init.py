"""init

Revision ID: 9969606c99a3
Revises: 
Create Date: 2026-03-15 04:33:52.789249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9969606c99a3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("subscription_expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("balance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("tenant_code", name=op.f("uq_tenants_tenant_code")),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_tenant_code"), "tenants", ["tenant_code"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_tenant_admin", sa.Boolean(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("wechat_openid", sa.String(length=100), nullable=True),
        sa.Column("real_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_users_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
        sa.UniqueConstraint("wechat_openid", name=op.f("uq_users_wechat_openid")),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("assigned_lawyer_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_lawyer_id"], ["users.id"], name=op.f("fk_cases_assigned_lawyer_id_users")),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_cases_client_id_users")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_cases_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
    )
    op.create_index(op.f("ix_cases_assigned_lawyer_id"), "cases", ["assigned_lawyer_id"], unique=False)
    op.create_index(op.f("ix_cases_case_number"), "cases", ["case_number"], unique=False)
    op.create_index(op.f("ix_cases_client_id"), "cases", ["client_id"], unique=False)
    op.create_index(op.f("ix_cases_id"), "cases", ["id"], unique=False)
    op.create_index(op.f("ix_cases_status"), "cases", ["status"], unique=False)
    op.create_index(op.f("ix_cases_tenant_id"), "cases", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_cases_title"), "cases", ["title"], unique=False)

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("uploader_id", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_files_case_id_cases")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_files_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], name=op.f("fk_files_uploader_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_files")),
    )
    op.create_index(op.f("ix_files_case_id"), "files", ["case_id"], unique=False)
    op.create_index(op.f("ix_files_id"), "files", ["id"], unique=False)
    op.create_index(op.f("ix_files_tenant_id"), "files", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_files_uploader_id"), "files", ["uploader_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_files_uploader_id"), table_name="files")
    op.drop_index(op.f("ix_files_tenant_id"), table_name="files")
    op.drop_index(op.f("ix_files_id"), table_name="files")
    op.drop_index(op.f("ix_files_case_id"), table_name="files")
    op.drop_table("files")

    op.drop_index(op.f("ix_cases_title"), table_name="cases")
    op.drop_index(op.f("ix_cases_tenant_id"), table_name="cases")
    op.drop_index(op.f("ix_cases_status"), table_name="cases")
    op.drop_index(op.f("ix_cases_id"), table_name="cases")
    op.drop_index(op.f("ix_cases_client_id"), table_name="cases")
    op.drop_index(op.f("ix_cases_case_number"), table_name="cases")
    op.drop_index(op.f("ix_cases_assigned_lawyer_id"), table_name="cases")
    op.drop_table("cases")

    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_tenants_tenant_code"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")
