"""add file access grants

Revision ID: 9f1e2d3c4b5a
Revises: 6f7a8b9c0d12
Create Date: 2026-03-24 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f1e2d3c4b5a"
down_revision: Union[str, Sequence[str], None] = "6f7a8b9c0d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_access_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("issued_to_user_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], name=op.f("fk_file_access_grants_file_id_files")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_file_access_grants")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_file_access_grants_token_hash")),
    )
    op.create_index(op.f("ix_file_access_grants_id"), "file_access_grants", ["id"], unique=False)
    op.create_index(op.f("ix_file_access_grants_file_id"), "file_access_grants", ["file_id"], unique=False)
    op.create_index(op.f("ix_file_access_grants_tenant_id"), "file_access_grants", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_file_access_grants_issued_to_user_id"), "file_access_grants", ["issued_to_user_id"], unique=False)
    op.create_index(op.f("ix_file_access_grants_token_hash"), "file_access_grants", ["token_hash"], unique=True)
    op.create_index(op.f("ix_file_access_grants_expires_at"), "file_access_grants", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_access_grants_expires_at"), table_name="file_access_grants")
    op.drop_index(op.f("ix_file_access_grants_token_hash"), table_name="file_access_grants")
    op.drop_index(op.f("ix_file_access_grants_issued_to_user_id"), table_name="file_access_grants")
    op.drop_index(op.f("ix_file_access_grants_tenant_id"), table_name="file_access_grants")
    op.drop_index(op.f("ix_file_access_grants_file_id"), table_name="file_access_grants")
    op.drop_index(op.f("ix_file_access_grants_id"), table_name="file_access_grants")
    op.drop_table("file_access_grants")
