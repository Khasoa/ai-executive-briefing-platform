# Database Migrations

## Why the schema drifted

Railway's `alembic_version` was stamped `001` while the live tables still matched the pre-Briefly **Atlas** shape (`crm_deals`, `research_items`, `tasks`, `meetings.time`, `emails.summary`, `daily_briefs.greeting`, users without `full_name` / `timezone` / `preferences`).

Revision `001` in this repository describes the **Briefly** schema. It was stamped on Railway without having been applied against that Atlas database. That is why services fell back to `demo_data` despite "sharing" revision `001`.

Revision history was **not** rewritten. Forward revisions repair the drift.

## Revision chain

| Revision | Purpose |
|----------|---------|
| `001` | Briefly initial schema (users, morning_briefs, brief_actions, meetings, emails, opportunities, integrations, sync_events). Kept as-is. |
| `002` | Adds `daily_briefs` (Phase 1 model missing from `001`). No-op if an Atlas-shaped `daily_briefs` already exists. |
| `003` | Aligns legacy Atlas databases with current models. On a fresh Briefly DB from `001`→`002`, mostly ensures indexes/constraints. On Atlas, rebuilds mismatched empty tables (or renames populated ones to `_legacy_*`), creates missing Briefly tables, drops obsolete Atlas-only tables. |

```
<base> → 001 → 002 → 003 (head)
```

## Fresh database

```bash
cd backend
alembic upgrade head
# then seed (see backend/README.md)
```

A completely empty PostgreSQL database reaches the current model shape through `001` → `002` → `003` with no manual steps.

## Existing Railway / Atlas database

```bash
cd backend
# Confirm current stamp
alembic current

# Apply 002 + 003. Empty Atlas tables are dropped and recreated in
# Briefly shape. Tables with rows are renamed to _legacy_<table> instead
# of deleted — inspect and backfill manually if that ever happens.
alembic upgrade head
```

Data safety rules in `003`:

1. Count rows before any destructive change.
2. If rows > 0 → `ALTER` rename to `_legacy_<table>` (never silent delete).
3. If rows == 0 → drop and recreate in Briefly shape.
4. Obsolete Atlas-only tables (`crm_deals`, `research_items`, `tasks`) follow the same rule.

## After upgrading

```bash
python3 scripts/seed.py
```

That entry point runs every domain seed in dependency order. Individual `scripts/seed_*.py` modules remain available for modular re-runs.

## Model ↔ migration parity

Every SQLAlchemy model under `app/models/` is registered in `alembic/env.py` via `app.models`. Indexes and unique constraints declared in `__table_args__` match revisions `001`–`003`:

- `uq_brief_per_user_per_day`, `ix_morning_briefs_user_date`
- `ix_brief_actions_brief`
- `ix_meetings_user_starts_at`
- `ix_emails_user_category`
- `ix_opportunities_user_risk`
- `uq_integration_per_user_provider`
- `ix_sync_events_integration_time`
