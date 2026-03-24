"""harden sms verification token persistence and verify lock

Revision ID: 8c3f2d1e4a6b
Revises: 7e2a1c5b9f10
Create Date: 2026-03-21 10:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c3f2d1e4a6b"
down_revision: Union[str, Sequence[str], None] = "7e2a1c5b9f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "sms_codes"):
        op.create_table(
            "sms_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("purpose", sa.String(length=20), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verify_fail_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verify_locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verification_token", sa.String(length=128), nullable=True),
            sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verification_consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_sms_codes")),
            sa.UniqueConstraint("request_id", name=op.f("uq_sms_codes_request_id")),
        )
        op.create_index(op.f("ix_sms_codes_id"), "sms_codes", ["id"], unique=False)
        op.create_index(op.f("ix_sms_codes_phone"), "sms_codes", ["phone"], unique=False)
        op.create_index(op.f("ix_sms_codes_purpose"), "sms_codes", ["purpose"], unique=False)
        op.create_index(op.f("ix_sms_codes_request_id"), "sms_codes", ["request_id"], unique=False)
        op.create_index(op.f("ix_sms_codes_expires_at"), "sms_codes", ["expires_at"], unique=False)
        op.create_index(op.f("ix_sms_codes_verification_token"), "sms_codes", ["verification_token"], unique=False)
        return

    existing_columns = _column_names(inspector, "sms_codes")
    if "verify_fail_count" not in existing_columns:
        op.add_column("sms_codes", sa.Column("verify_fail_count", sa.Integer(), nullable=False, server_default="0"))
    if "verify_locked_until" not in existing_columns:
        op.add_column("sms_codes", sa.Column("verify_locked_until", sa.DateTime(timezone=True), nullable=True))
    if "verification_token" not in existing_columns:
        op.add_column("sms_codes", sa.Column("verification_token", sa.String(length=128), nullable=True))
    if "verification_expires_at" not in existing_columns:
        op.add_column("sms_codes", sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "verification_consumed_at" not in existing_columns:
        op.add_column("sms_codes", sa.Column("verification_consumed_at", sa.DateTime(timezone=True), nullable=True))

    existing_indexes = _index_names(inspector, "sms_codes")
    verification_token_index = op.f("ix_sms_codes_verification_token")
    if verification_token_index not in existing_indexes:
        op.create_index(verification_token_index, "sms_codes", ["verification_token"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "sms_codes"):
        return

    existing_indexes = _index_names(inspector, "sms_codes")
    verification_token_index = op.f("ix_sms_codes_verification_token")
    if verification_token_index in existing_indexes:
        op.drop_index(verification_token_index, table_name="sms_codes")

    existing_columns = _column_names(inspector, "sms_codes")
    if "verification_consumed_at" in existing_columns:
        op.drop_column("sms_codes", "verification_consumed_at")
    if "verification_expires_at" in existing_columns:
        op.drop_column("sms_codes", "verification_expires_at")
    if "verification_token" in existing_columns:
        op.drop_column("sms_codes", "verification_token")
    if "verify_locked_until" in existing_columns:
        op.drop_column("sms_codes", "verify_locked_until")
    if "verify_fail_count" in existing_columns:
        op.drop_column("sms_codes", "verify_fail_count")
