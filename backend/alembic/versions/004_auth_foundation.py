"""Auth foundation: passwords, refresh tokens, daily_briefs ownership

Revision ID: 004
Revises: 003
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user", "refresh_tokens", ["user_id"])

    op.add_column(
        "daily_briefs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE daily_briefs
        SET user_id = (SELECT id FROM users ORDER BY created_at ASC NULLS LAST LIMIT 1)
        WHERE user_id IS NULL
          AND EXISTS (SELECT 1 FROM users)
        """
    )
    op.execute("DELETE FROM daily_briefs WHERE user_id IS NULL")
    op.alter_column("daily_briefs", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_daily_briefs_user_id_users",
        "daily_briefs",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index(
        "ix_daily_briefs_user_generated",
        "daily_briefs",
        ["user_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_daily_briefs_user_generated", table_name="daily_briefs")
    op.drop_constraint("fk_daily_briefs_user_id_users", "daily_briefs", type_="foreignkey")
    op.drop_column("daily_briefs", "user_id")

    op.drop_index("ix_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_column("users", "hashed_password")
