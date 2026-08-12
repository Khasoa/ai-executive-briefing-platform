"""Weekly email digests

Revision ID: 010
Revises: 009
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weekly_digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("planning_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("generated_by", sa.String(length=20), nullable=False, server_default="curated"),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("email_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "sections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_digest_user_week"),
    )
    op.create_index("ix_weekly_digests_user_week", "weekly_digests", ["user_id", "week_start"])


def downgrade() -> None:
    op.drop_index("ix_weekly_digests_user_week", table_name="weekly_digests")
    op.drop_table("weekly_digests")
