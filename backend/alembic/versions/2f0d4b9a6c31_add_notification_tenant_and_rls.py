"""add notification tenant and rls

Revision ID: 2f0d4b9a6c31
Revises: 9d40948c2cb1
Create Date: 2026-03-15 23:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f0d4b9a6c31"
down_revision: Union[str, Sequence[str], None] = "9d40948c2cb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = ["users", "cases", "files", "invites", "notifications"]
RLS_EXPRESSION = "tenant_id = nullif(current_setting('app.current_tenant', true), '')::int"


def _drop_policy(table_name: str) -> None:
    op.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"))


def _create_policy(table_name: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY tenant_isolation ON {table_name}
            USING ({RLS_EXPRESSION})
            WITH CHECK ({RLS_EXPRESSION})
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("notifications", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE notifications AS n
            SET tenant_id = u.tenant_id
            FROM users AS u
            WHERE n.user_id = u.id
            """
        )
    )
    op.alter_column("notifications", "tenant_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_notifications_tenant_id_tenants"),
        "notifications",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(op.f("ix_notifications_tenant_id"), "notifications", ["tenant_id"], unique=False)

    for table_name in RLS_TABLES:
        _drop_policy(table_name)
        _create_policy(table_name)


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in reversed(RLS_TABLES):
        _drop_policy(table_name)
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))

    op.drop_index(op.f("ix_notifications_tenant_id"), table_name="notifications")
    op.drop_constraint(op.f("fk_notifications_tenant_id_tenants"), "notifications", type_="foreignkey")
    op.drop_column("notifications", "tenant_id")
