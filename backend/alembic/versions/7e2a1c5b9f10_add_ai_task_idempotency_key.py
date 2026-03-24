"""add ai task idempotency key and sms code table

Revision ID: 7e2a1c5b9f10
Revises: 4b3e21c8f9d7
Create Date: 2026-03-19 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e2a1c5b9f10"
down_revision: Union[str, Sequence[str], None] = "4b3e21c8f9d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_EXPRESSION = "tenant_id = nullif(current_setting('app.current_tenant', true), '')::int OR current_setting('app.is_super_admin', true) = '1'"


def upgrade() -> None:
    op.add_column("ai_tasks", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_ai_tasks_idempotency_key"), "ai_tasks", ["idempotency_key"], unique=False)
    op.create_unique_constraint(
        op.f("uq_ai_tasks_idempotency_scope"),
        "ai_tasks",
        ["tenant_id", "case_id", "task_type", "created_by", "idempotency_key"],
    )

    op.create_table(
        "sms_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sms_codes")),
        sa.UniqueConstraint("request_id", name=op.f("uq_sms_codes_request_id")),
    )
    op.create_index(op.f("ix_sms_codes_id"), "sms_codes", ["id"], unique=False)
    op.create_index(op.f("ix_sms_codes_phone"), "sms_codes", ["phone"], unique=False)
    op.create_index(op.f("ix_sms_codes_purpose"), "sms_codes", ["purpose"], unique=False)
    op.create_index(op.f("ix_sms_codes_request_id"), "sms_codes", ["request_id"], unique=False)
    op.create_index(op.f("ix_sms_codes_expires_at"), "sms_codes", ["expires_at"], unique=False)

    op.execute(sa.text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON users"))
    op.execute(sa.text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY tenant_isolation ON users
            USING ({RLS_EXPRESSION})
            WITH CHECK ({RLS_EXPRESSION})
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON users"))
    op.execute(sa.text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY tenant_isolation ON users
            USING (tenant_id = nullif(current_setting('app.current_tenant', true), '')::int)
            WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant', true), '')::int)
            """
        )
    )

    op.drop_index(op.f("ix_sms_codes_expires_at"), table_name="sms_codes")
    op.drop_index(op.f("ix_sms_codes_request_id"), table_name="sms_codes")
    op.drop_index(op.f("ix_sms_codes_purpose"), table_name="sms_codes")
    op.drop_index(op.f("ix_sms_codes_phone"), table_name="sms_codes")
    op.drop_index(op.f("ix_sms_codes_id"), table_name="sms_codes")
    op.drop_table("sms_codes")

    op.drop_constraint(op.f("uq_ai_tasks_idempotency_scope"), "ai_tasks", type_="unique")
    op.drop_index(op.f("ix_ai_tasks_idempotency_key"), table_name="ai_tasks")
    op.drop_column("ai_tasks", "idempotency_key")
