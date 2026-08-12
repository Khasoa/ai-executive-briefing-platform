"""Notion synced items

Revision ID: 009
Revises: 008
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notion_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("object_type", sa.String(length=30), nullable=False, server_default="page"),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="note"),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("parent_database_id", sa.String(length=255), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("content_preview", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "intelligence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
    )
    op.create_index("ix_notion_items_user_kind", "notion_items", ["user_id", "kind"])
    op.create_index("ix_notion_items_user_edited", "notion_items", ["user_id", "last_edited_at"])
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notion_items_user_external
        ON notion_items (user_id, external_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_notion_items_user_external")
    op.drop_index("ix_notion_items_user_edited", table_name="notion_items")
    op.drop_index("ix_notion_items_user_kind", table_name="notion_items")
    op.drop_table("notion_items")
