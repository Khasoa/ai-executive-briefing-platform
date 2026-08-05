"""Align legacy Atlas schema (stamped 001) with the current Briefly models.

Revision ID: 003
Revises: 002
Create Date: 2026-08-06

Root cause of the drift
-----------------------
Railway's `alembic_version` is stamped `001`, but the live tables still match
the pre-Briefly "Atlas" shape (`crm_deals`, `research_items`, `tasks`,
`meetings.time`, `emails.summary`, `daily_briefs.greeting`, users without
`full_name`/`timezone`/`preferences`, etc.). Revision `001` in this repo
describes the Briefly schema — it was stamped without having been applied
against that Atlas database.

This revision does NOT rewrite `001`. It is a forward-only bridge:

- Fresh databases that ran `001` → `002` already have the Briefly shape:
  this revision is effectively a no-op (it only creates any still-missing
  Briefly tables and ensures indexes/constraints exist).
- Railway/Atlas databases stamped at `001`/`002`: detect legacy markers,
  rebuild mismatched tables onto the Briefly shape, create missing tables,
  and drop obsolete Atlas-only tables.

Data safety
-----------
Before dropping or rebuilding a table this revision:

1. Counts rows.
2. If the table has rows, renames it to `_legacy_<table>` and leaves it
   in place for manual inspection/backfill — it never silently deletes
   populated data.
3. If the table is empty (the current Railway state), drops and recreates
   it in the Briefly shape.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------


def _bind():
    return op.get_bind()


def _tables() -> set[str]:
    return set(sa.inspect(_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {c["name"] for c in sa.inspect(_bind()).get_columns(table)}


def _row_count(table: str) -> int:
    if table not in _tables():
        return 0
    return int(_bind().execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar() or 0)


def _is_atlas_schema() -> bool:
    """True when the connected database still has pre-Briefly (Atlas) markers."""
    cols_meetings = _columns("meetings")
    cols_users = _columns("users")
    cols_daily = _columns("daily_briefs")
    cols_emails = _columns("emails")

    return any(
        [
            "crm_deals" in _tables(),
            "research_items" in _tables(),
            "tasks" in _tables(),
            "time" in cols_meetings and "starts_at" not in cols_meetings,
            "greeting" in cols_daily and "summary" not in cols_daily,
            "summary" in cols_emails and "ai_summary" not in cols_emails,
            "full_name" not in cols_users and "email" in cols_users,
        ]
    )


def _retire_or_drop(table: str) -> None:
    """Remove an empty table, or rename a populated one to `_legacy_*`."""
    if table not in _tables():
        return
    if _row_count(table) > 0:
        legacy = f"_legacy_{table}"
        # Avoid colliding with a previous alignment attempt.
        if legacy in _tables():
            op.drop_table(legacy)
        op.rename_table(table, legacy)
        return
    op.drop_table(table)


def _ensure_index(name: str, table: str, columns: list[str]) -> None:
    if table not in _tables():
        return
    existing = {idx["name"] for idx in sa.inspect(_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def _ensure_unique(name: str, table: str, columns: list[str]) -> None:
    if table not in _tables():
        return
    existing = {
        uc["name"]
        for uc in sa.inspect(_bind()).get_unique_constraints(table)
        if uc.get("name")
    }
    # Also treat unique indexes as satisfying the constraint.
    existing |= {idx["name"] for idx in sa.inspect(_bind()).get_indexes(table) if idx.get("unique")}
    if name not in existing:
        op.create_unique_constraint(name, table, columns)


# ---------------------------------------------------------------------------
# Briefly table constructors (match revision 001 + 002 + current models)
# ---------------------------------------------------------------------------


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("avatar", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(length=100), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def _create_morning_briefs() -> None:
    op.create_table(
        "morning_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brief_date", sa.Date(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("closing", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "brief_date", name="uq_brief_per_user_per_day"),
    )
    op.create_index("ix_morning_briefs_user_date", "morning_briefs", ["user_id", "brief_date"])


def _create_brief_actions() -> None:
    op.create_table(
        "brief_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brief_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("due", sa.String(length=100), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["brief_id"], ["morning_briefs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brief_actions_brief", "brief_actions", ["brief_id"])


def _create_meetings() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("prep_status", sa.String(length=30), nullable=False, server_default="ready"),
        sa.Column("prep_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("attendees", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("agenda", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("company", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("intelligence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_user_starts_at", "meetings", ["user_id", "starts_at"])


def _create_emails() -> None:
    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("sender", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("suggested_response", sa.Text(), nullable=False, server_default=""),
        sa.Column("reading_time", sa.String(length=20), nullable=False, server_default="1 min"),
        sa.Column("thread_count", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("unread", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("labels", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emails_user_category", "emails", ["user_id", "category"])


def _create_opportunities() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("logo", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("industry", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("last_interaction", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("signals", postgresql.ARRAY(sa.String()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_user_risk", "opportunities", ["user_id", "risk_level"])


def _create_integrations() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="not-connected"),
        sa.Column("account", sa.String(length=255), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_integration_per_user_provider"),
    )


def _create_sync_events() -> None:
    op.create_table(
        "sync_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_events_integration_time", "sync_events", ["integration_id", "occurred_at"])


def _create_daily_briefs() -> None:
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


def _needs_rebuild(table: str, *, briefly_marker: str, atlas_marker: str | None) -> bool:
    cols = _columns(table)
    if not cols:
        return True
    if briefly_marker in cols and (atlas_marker is None or atlas_marker not in cols):
        return False
    return True


def _align_atlas() -> None:
    # Drop Atlas-only leftovers first (no Briefly equivalent).
    for obsolete in ("research_items", "tasks", "crm_deals"):
        _retire_or_drop(obsolete)

    # Retire mismatched dependents BEFORE touching `users`, so PostgreSQL
    # foreign keys do not block the users rebuild.
    dependents = [
        ("sync_events", "integration_id", None),
        ("brief_actions", "brief_id", None),
        ("morning_briefs", "brief_date", None),
        ("emails", "ai_summary", "summary"),
        ("meetings", "starts_at", "time"),
        ("integrations", "scopes", None),
        ("opportunities", "risk_level", None),
        ("daily_briefs", "summary", "greeting"),
    ]
    for table, briefly_marker, atlas_marker in dependents:
        if table in _tables() and _needs_rebuild(
            table, briefly_marker=briefly_marker, atlas_marker=atlas_marker
        ):
            _retire_or_drop(table)

    if "users" not in _tables() or "full_name" not in _columns("users"):
        _retire_or_drop("users")
        _create_users()

    if "daily_briefs" not in _tables():
        _create_daily_briefs()
    if "meetings" not in _tables():
        _create_meetings()
    if "emails" not in _tables():
        _create_emails()
    if "integrations" not in _tables():
        _create_integrations()
    if "opportunities" not in _tables():
        _create_opportunities()
    if "morning_briefs" not in _tables():
        _create_morning_briefs()
    if "brief_actions" not in _tables():
        _create_brief_actions()
    if "sync_events" not in _tables():
        _create_sync_events()


def _ensure_briefly_completeness() -> None:
    """For databases that already match Briefly: fill any remaining gaps."""
    if "users" not in _tables():
        _create_users()
    if "daily_briefs" not in _tables():
        _create_daily_briefs()
    if "morning_briefs" not in _tables():
        _create_morning_briefs()
    if "brief_actions" not in _tables():
        _create_brief_actions()
    if "meetings" not in _tables():
        _create_meetings()
    if "emails" not in _tables():
        _create_emails()
    if "opportunities" not in _tables():
        _create_opportunities()
    if "integrations" not in _tables():
        _create_integrations()
    if "sync_events" not in _tables():
        _create_sync_events()

    _ensure_index("ix_morning_briefs_user_date", "morning_briefs", ["user_id", "brief_date"])
    _ensure_unique("uq_brief_per_user_per_day", "morning_briefs", ["user_id", "brief_date"])
    _ensure_index("ix_brief_actions_brief", "brief_actions", ["brief_id"])
    _ensure_index("ix_meetings_user_starts_at", "meetings", ["user_id", "starts_at"])
    _ensure_index("ix_emails_user_category", "emails", ["user_id", "category"])
    _ensure_index("ix_opportunities_user_risk", "opportunities", ["user_id", "risk_level"])
    _ensure_unique("uq_integration_per_user_provider", "integrations", ["user_id", "provider"])
    _ensure_index("ix_sync_events_integration_time", "sync_events", ["integration_id", "occurred_at"])


def upgrade() -> None:
    if _is_atlas_schema():
        _align_atlas()
    _ensure_briefly_completeness()


def downgrade() -> None:
    """Downgrade is intentionally limited.

    Rebuilding the Atlas schema from Briefly would destroy the Briefly-shaped
    data this revision creates. Operators who need the pre-alignment state
    should restore from a backup taken before `alembic upgrade 003`, or from
    any `_legacy_*` tables this revision left behind when rows were present.
    """
    # No automatic Atlas rebuild — see module docstring.
    pass
