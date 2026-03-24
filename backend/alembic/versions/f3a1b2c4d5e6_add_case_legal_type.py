"""add case legal_type

Revision ID: f3a1b2c4d5e6
Revises: c6e7f8a9b012
Create Date: 2026-03-23 11:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a1b2c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c6e7f8a9b012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("legal_type", sa.String(length=50), nullable=False, server_default="other"),
    )
    op.create_index("ix_cases_legal_type", "cases", ["legal_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cases_legal_type", table_name="cases")
    op.drop_column("cases", "legal_type")
