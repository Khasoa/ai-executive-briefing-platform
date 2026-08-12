"""Provider-neutral work_items for monday.com + ClickUp

Revision ID: 012
Revises: 011
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", sa.String(length=255), nullable=True),
        sa.Column("workspace_name", sa.String(length=255), nullable=True),
        sa.Column("container_id", sa.String(length=255), nullable=True),
        sa.Column("container_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=40), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee_name", sa.String(length=255), nullable=True),
        sa.Column("assignee_external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("parent_external_id", sa.String(length=255), nullable=True),
        sa.Column(
            "labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "intelligence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "external_id",
            name="uq_work_items_user_provider_external",
        ),
    )
    op.create_index("ix_work_items_user_provider", "work_items", ["user_id", "provider"])
    op.create_index("ix_work_items_user_due", "work_items", ["user_id", "due_at"])
    op.create_index("ix_work_items_user_status", "work_items", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_work_items_user_status", table_name="work_items")
    op.drop_index("ix_work_items_user_due", table_name="work_items")
    op.drop_index("ix_work_items_user_provider", table_name="work_items")
    op.drop_table("work_items")
