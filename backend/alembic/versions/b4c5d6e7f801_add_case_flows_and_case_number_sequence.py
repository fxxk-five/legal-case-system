"""add case flows, case number sequences, and analysis/file fields

Revision ID: b4c5d6e7f801
Revises: 8c3f2d1e4a6b
Create Date: 2026-03-22 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f801"
down_revision: Union[str, Sequence[str], None] = "8c3f2d1e4a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("operator_name", sa.String(length=100), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visible_to", sa.String(length=20), server_default="both", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_case_flows_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_case_flows_case_id_cases")),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], name=op.f("fk_case_flows_operator_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_flows")),
    )
    op.create_index(op.f("ix_case_flows_id"), "case_flows", ["id"], unique=False)
    op.create_index(op.f("ix_case_flows_tenant_id"), "case_flows", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_case_flows_case_id"), "case_flows", ["case_id"], unique=False)
    op.create_index(op.f("ix_case_flows_operator_id"), "case_flows", ["operator_id"], unique=False)
    op.create_index(op.f("ix_case_flows_action_type"), "case_flows", ["action_type"], unique=False)
    op.create_index(op.f("ix_case_flows_visible_to"), "case_flows", ["visible_to"], unique=False)
    op.create_index(op.f("ix_case_flows_created_at"), "case_flows", ["created_at"], unique=False)

    op.create_table(
        "case_number_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_case_number_sequences_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_number_sequences")),
        sa.UniqueConstraint("tenant_id", "year", name="uq_case_number_sequences_tenant_year"),
    )
    op.create_index(op.f("ix_case_number_sequences_id"), "case_number_sequences", ["id"], unique=False)
    op.create_index(op.f("ix_case_number_sequences_tenant_id"), "case_number_sequences", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_case_number_sequences_year"), "case_number_sequences", ["year"], unique=False)

    op.add_column("cases", sa.Column("analysis_status", sa.String(length=30), nullable=True, server_default="not_started"))
    op.add_column("cases", sa.Column("analysis_progress", sa.Integer(), nullable=True, server_default="0"))
    op.create_index(op.f("ix_cases_analysis_status"), "cases", ["analysis_status"], unique=False)

    op.add_column("files", sa.Column("uploader_role", sa.String(length=20), nullable=True, server_default="lawyer"))
    op.add_column("files", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("files", sa.Column("parse_status", sa.String(length=30), nullable=True, server_default="pending"))
    op.create_index(op.f("ix_files_uploader_role"), "files", ["uploader_role"], unique=False)
    op.create_index(op.f("ix_files_parse_status"), "files", ["parse_status"], unique=False)

    op.execute(
        sa.text(
            """
            UPDATE files
            SET uploader_role = CASE
                WHEN lower(coalesce(users.role, '')) = 'client' THEN 'client'
                ELSE 'lawyer'
            END
            FROM users
            WHERE files.uploader_id = users.id AND files.uploader_role IS NULL
            """
        )
    )
    op.execute(sa.text("UPDATE files SET uploader_role = 'lawyer' WHERE uploader_role IS NULL"))
    op.execute(sa.text("UPDATE files SET parse_status = 'pending' WHERE parse_status IS NULL"))
    op.execute(sa.text("UPDATE cases SET analysis_status = 'not_started' WHERE analysis_status IS NULL"))
    op.execute(sa.text("UPDATE cases SET analysis_progress = 0 WHERE analysis_progress IS NULL"))

    op.alter_column("files", "uploader_role", existing_type=sa.String(length=20), nullable=False)
    op.alter_column("files", "parse_status", existing_type=sa.String(length=30), nullable=False)
    op.alter_column("cases", "analysis_status", existing_type=sa.String(length=30), nullable=False)
    op.alter_column("cases", "analysis_progress", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("cases", "analysis_progress", existing_type=sa.Integer(), nullable=True)
    op.alter_column("cases", "analysis_status", existing_type=sa.String(length=30), nullable=True)
    op.alter_column("files", "parse_status", existing_type=sa.String(length=30), nullable=True)
    op.alter_column("files", "uploader_role", existing_type=sa.String(length=20), nullable=True)

    op.drop_index(op.f("ix_files_parse_status"), table_name="files")
    op.drop_index(op.f("ix_files_uploader_role"), table_name="files")
    op.drop_column("files", "parse_status")
    op.drop_column("files", "description")
    op.drop_column("files", "uploader_role")

    op.drop_index(op.f("ix_cases_analysis_status"), table_name="cases")
    op.drop_column("cases", "analysis_progress")
    op.drop_column("cases", "analysis_status")

    op.drop_index(op.f("ix_case_number_sequences_year"), table_name="case_number_sequences")
    op.drop_index(op.f("ix_case_number_sequences_tenant_id"), table_name="case_number_sequences")
    op.drop_index(op.f("ix_case_number_sequences_id"), table_name="case_number_sequences")
    op.drop_table("case_number_sequences")

    op.drop_index(op.f("ix_case_flows_created_at"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_visible_to"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_action_type"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_operator_id"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_case_id"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_tenant_id"), table_name="case_flows")
    op.drop_index(op.f("ix_case_flows_id"), table_name="case_flows")
    op.drop_table("case_flows")
