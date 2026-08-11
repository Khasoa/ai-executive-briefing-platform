"""Google OAuth: state + login ticket tables

Revision ID: 005
Revises: 004
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state"),
    )
    op.create_index("ix_oauth_states_provider_expires", "oauth_states", ["provider", "expires_at"])

    op.create_table(
        "oauth_login_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_hash"),
    )
    op.create_index(
        "ix_oauth_login_tickets_expires",
        "oauth_login_tickets",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_login_tickets_expires", table_name="oauth_login_tickets")
    op.drop_table("oauth_login_tickets")
    op.drop_index("ix_oauth_states_provider_expires", table_name="oauth_states")
    op.drop_table("oauth_states")
