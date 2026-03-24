"""add ai budget fields for tenant and case

Revision ID: c6e7f8a9b012
Revises: b4c5d6e7f801
Create Date: 2026-03-22 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6e7f8a9b012"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("ai_monthly_budget_limit", sa.Numeric(12, 2), nullable=True))
    op.add_column("tenants", sa.Column("ai_budget_degrade_model", sa.String(length=100), nullable=True))
    op.add_column("cases", sa.Column("ai_case_budget_limit", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "ai_case_budget_limit")
    op.drop_column("tenants", "ai_budget_degrade_model")
    op.drop_column("tenants", "ai_monthly_budget_limit")
