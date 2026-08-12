"""Opportunity sync: unique external CRM ids

Revision ID: 011
Revises: 010
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_opportunities_user_external
        ON opportunities (user_id, external_id)
        WHERE external_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_opportunities_user_external")
