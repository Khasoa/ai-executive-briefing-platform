"""Add daily_briefs (Phase 1 model missing from revision 001).

Revision ID: 002
Revises: 001
Create Date: 2026-08-06

Why this revision exists
------------------------
Revision `001` created the Briefly domain tables but was authored before
`DailyBrief` landed in the codebase. Rather than rewrite `001` (which is
already stamped on Railway as the current head), this revision adds the
missing table for fresh databases that ran `001` cleanly.

If `daily_briefs` already exists under the legacy Atlas shape (Railway
today), this revision is a deliberate no-op — revision `003` owns the
Atlas → Briefly alignment so we never silently drop a live table here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    # Fresh install after `001`: create the Briefly-shaped table.
    # Atlas/Railway already has a differently-shaped `daily_briefs` — leave
    # it for `003`, which detects legacy columns and rebuilds safely.
    if _table_exists("daily_briefs"):
        return

    op.create_table(
        "daily_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priorities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("executive_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Only drop the Briefly-shaped table we created. Never drop an Atlas
    # `daily_briefs` that `upgrade()` skipped over.
    if not _table_exists("daily_briefs"):
        return

    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("daily_briefs")}
    if "summary" in columns and "greeting" not in columns:
        op.drop_table("daily_briefs")
