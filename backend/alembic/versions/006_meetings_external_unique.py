"""Google Calendar sync: unique external meeting ids

Revision ID: 006
Revises: 005
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent Calendar sync keys meetings by (user_id, external_id).
    # Partial unique index ignores curated/demo rows with NULL external_id.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_meetings_user_external
        ON meetings (user_id, external_id)
        WHERE external_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_meetings_user_external")
