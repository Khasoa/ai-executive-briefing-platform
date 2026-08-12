"""Gmail sync: unique external email ids

Revision ID: 007
Revises: 006
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent Gmail sync keys emails by (user_id, external_id).
    # Partial unique index ignores curated/demo rows with NULL external_id.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_emails_user_external
        ON emails (user_id, external_id)
        WHERE external_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_emails_user_external")
