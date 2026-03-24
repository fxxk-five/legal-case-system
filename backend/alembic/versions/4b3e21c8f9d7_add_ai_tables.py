"""add ai tables

Revision ID: 4b3e21c8f9d7
Revises: 2f0d4b9a6c31
Create Date: 2026-03-19 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b3e21c8f9d7"
down_revision: Union[str, Sequence[str], None] = "2f0d4b9a6c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.Column("fact_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_case_facts_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_case_facts_case_id_cases")),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], name=op.f("fk_case_facts_file_id_files")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_case_facts_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_facts")),
    )
    op.create_index(op.f("ix_case_facts_id"), "case_facts", ["id"], unique=False)
    op.create_index(op.f("ix_case_facts_tenant_id"), "case_facts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_case_facts_case_id"), "case_facts", ["case_id"], unique=False)
    op.create_index(op.f("ix_case_facts_file_id"), "case_facts", ["file_id"], unique=False)
    op.create_index(op.f("ix_case_facts_fact_type"), "case_facts", ["fact_type"], unique=False)
    op.create_index(op.f("ix_case_facts_confidence"), "case_facts", ["confidence"], unique=False)
    op.create_index(op.f("ix_case_facts_created_by"), "case_facts", ["created_by"], unique=False)

    op.create_table(
        "ai_analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type", sa.String(length=50), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("applicable_laws", sa.JSON(), nullable=False),
        sa.Column("related_cases", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("ai_model", sa.String(length=100), nullable=False),
        sa.Column("token_usage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_ai_analysis_results_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_ai_analysis_results_case_id_cases")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_ai_analysis_results_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_analysis_results")),
    )
    op.create_index(op.f("ix_ai_analysis_results_id"), "ai_analysis_results", ["id"], unique=False)
    op.create_index(op.f("ix_ai_analysis_results_tenant_id"), "ai_analysis_results", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_ai_analysis_results_case_id"), "ai_analysis_results", ["case_id"], unique=False)
    op.create_index(op.f("ix_ai_analysis_results_analysis_type"), "ai_analysis_results", ["analysis_type"], unique=False)
    op.create_index(op.f("ix_ai_analysis_results_created_by"), "ai_analysis_results", ["created_by"], unique=False)

    op.create_table(
        "falsification_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=True),
        sa.Column("challenge_type", sa.String(length=50), nullable=False),
        sa.Column("challenge_question", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("is_falsified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("improvement_suggestion", sa.Text(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ai_model", sa.String(length=100), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_falsification_records_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_falsification_records_case_id_cases")),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analysis_results.id"], name=op.f("fk_falsification_records_analysis_id_ai_analysis_results")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_falsification_records_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_falsification_records")),
    )
    op.create_index(op.f("ix_falsification_records_id"), "falsification_records", ["id"], unique=False)
    op.create_index(op.f("ix_falsification_records_tenant_id"), "falsification_records", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_falsification_records_case_id"), "falsification_records", ["case_id"], unique=False)
    op.create_index(op.f("ix_falsification_records_analysis_id"), "falsification_records", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_falsification_records_is_falsified"), "falsification_records", ["is_falsified"], unique=False)
    op.create_index(op.f("ix_falsification_records_created_by"), "falsification_records", ["created_by"], unique=False)

    op.create_table(
        "ai_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("input_params", sa.JSON(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_ai_tasks_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_ai_tasks_case_id_cases")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_ai_tasks_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_tasks")),
        sa.UniqueConstraint("task_id", name=op.f("uq_ai_tasks_task_id")),
    )
    op.create_index(op.f("ix_ai_tasks_id"), "ai_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_ai_tasks_task_id"), "ai_tasks", ["task_id"], unique=False)
    op.create_index(op.f("ix_ai_tasks_tenant_id"), "ai_tasks", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_ai_tasks_case_id"), "ai_tasks", ["case_id"], unique=False)
    op.create_index(op.f("ix_ai_tasks_task_type"), "ai_tasks", ["task_type"], unique=False)
    op.create_index(op.f("ix_ai_tasks_status"), "ai_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_ai_tasks_request_id"), "ai_tasks", ["request_id"], unique=False)
    op.create_index(op.f("ix_ai_tasks_created_by"), "ai_tasks", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_tasks_created_by"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_request_id"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_status"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_task_type"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_case_id"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_tenant_id"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_task_id"), table_name="ai_tasks")
    op.drop_index(op.f("ix_ai_tasks_id"), table_name="ai_tasks")
    op.drop_table("ai_tasks")

    op.drop_index(op.f("ix_falsification_records_created_by"), table_name="falsification_records")
    op.drop_index(op.f("ix_falsification_records_is_falsified"), table_name="falsification_records")
    op.drop_index(op.f("ix_falsification_records_analysis_id"), table_name="falsification_records")
    op.drop_index(op.f("ix_falsification_records_case_id"), table_name="falsification_records")
    op.drop_index(op.f("ix_falsification_records_tenant_id"), table_name="falsification_records")
    op.drop_index(op.f("ix_falsification_records_id"), table_name="falsification_records")
    op.drop_table("falsification_records")

    op.drop_index(op.f("ix_ai_analysis_results_created_by"), table_name="ai_analysis_results")
    op.drop_index(op.f("ix_ai_analysis_results_analysis_type"), table_name="ai_analysis_results")
    op.drop_index(op.f("ix_ai_analysis_results_case_id"), table_name="ai_analysis_results")
    op.drop_index(op.f("ix_ai_analysis_results_tenant_id"), table_name="ai_analysis_results")
    op.drop_index(op.f("ix_ai_analysis_results_id"), table_name="ai_analysis_results")
    op.drop_table("ai_analysis_results")

    op.drop_index(op.f("ix_case_facts_created_by"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_confidence"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_fact_type"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_file_id"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_case_id"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_tenant_id"), table_name="case_facts")
    op.drop_index(op.f("ix_case_facts_id"), table_name="case_facts")
    op.drop_table("case_facts")
