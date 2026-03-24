"""add tenant ai console settings

Revision ID: 2b3c4d5e6f70
Revises: 1a2b3c4d5e7f
Create Date: 2026-03-23 16:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f70"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("ai_prompt_settings", sa.JSON(), nullable=True))
    op.add_column("tenants", sa.Column("ai_provider_settings", sa.JSON(), nullable=True))
    op.add_column("tenants", sa.Column("ai_provider_locked", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("tenants", "ai_provider_locked")
    op.drop_column("tenants", "ai_provider_settings")
    op.drop_column("tenants", "ai_prompt_settings")
