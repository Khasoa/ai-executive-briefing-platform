"""Seed several realistic Integration rows into PostgreSQL.

Usage (from backend/):

    python scripts/seed_integrations.py

Run this only after applying the Alembic migration that creates the current
`integrations` shape (provider/status/account/scopes/config/last_sync_at/
connected_at — see `app.models.Integration`). This script writes directly
through the `Integration` ORM model. `IntegrationService` owns reads and
sync-triggered writes (`status` / `SyncEvent`) but has no "create
connection" path yet — that waits on OAuth. Integrations need a
`user_id`, so this script also finds or creates a demo user matching
`mock_data.USER`.

This does not touch authentication or OAuth: `config` here holds only the
display metadata (name/category/description/metrics/poweredBy) that the
model has no dedicated columns for — no real tokens are stored or read.
Providers match `mock_data.INTEGRATIONS` (Calendar, Gmail, Notion,
GoHighLevel, OpenAI, n8n).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allows `python scripts/seed_integrations.py` to work without installing
# the package: put the backend root (this file's grandparent) on the path
# so `from app...` resolves the same way it does under uvicorn, and put
# this file's own directory on the path so `seed_common` resolves too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Integration  # noqa: E402
from seed_common import get_or_create_demo_user, seed_idempotently  # noqa: E402

_NOW = datetime.now(timezone.utc)


def _minutes_ago(minutes: int) -> datetime:
    return _NOW - timedelta(minutes=minutes)


INTEGRATIONS = [
    dict(
        provider="google-calendar",
        status="connected",
        account="lydia@arcadiasystems.com",
        scopes=["calendar.readonly", "calendar.events.readonly"],
        last_sync_at=_minutes_ago(4),
        connected_at=_NOW - timedelta(days=180),
        config={
            "name": "Google Calendar",
            "category": "Calendar",
            "description": "Meetings, attendees and scheduling context for meeting intelligence.",
            "metrics": [
                {"label": "Meetings today", "value": "4"},
                {"label": "Calendars", "value": "2"},
            ],
            "poweredBy": "Google Workspace API",
        },
    ),
    dict(
        provider="gmail",
        status="connected",
        account="lydia@arcadiasystems.com",
        scopes=["gmail.readonly", "gmail.metadata"],
        last_sync_at=_minutes_ago(3),
        connected_at=_NOW - timedelta(days=180),
        config={
            "name": "Gmail",
            "category": "Email",
            "description": "Thread summarisation, prioritisation and suggested responses.",
            "metrics": [
                {"label": "Threads indexed", "value": "24"},
                {"label": "Needs reply", "value": "6"},
            ],
            "poweredBy": "Google Workspace API",
        },
    ),
    dict(
        provider="notion",
        status="connected",
        account="Arcadia Systems workspace",
        scopes=["read_content"],
        last_sync_at=_minutes_ago(42),
        connected_at=_NOW - timedelta(days=120),
        config={
            "name": "Notion",
            "category": "Knowledge",
            "description": "Plans, metrics and documents that give the brief its internal context.",
            "metrics": [
                {"label": "Pages indexed", "value": "12"},
                {"label": "Databases", "value": "3"},
            ],
            "poweredBy": "Notion API",
        },
    ),
    dict(
        provider="gohighlevel",
        status="syncing",
        account="Arcadia Systems · Location 4821",
        scopes=["opportunities.readonly", "contacts.readonly"],
        last_sync_at=_minutes_ago(1),
        connected_at=_NOW - timedelta(days=90),
        config={
            "name": "GoHighLevel",
            "category": "CRM",
            "description": "Opportunities, stages and interaction history behind pipeline intelligence.",
            "metrics": [
                {"label": "Opportunities", "value": "6"},
                {"label": "Pipeline", "value": "$2.6M"},
            ],
            "poweredBy": "GoHighLevel API v2",
        },
    ),
    dict(
        provider="openai",
        status="connected",
        account="Organisation · arcadia-systems",
        scopes=["responses.write"],
        last_sync_at=_minutes_ago(2),
        connected_at=_NOW - timedelta(days=200),
        config={
            "name": "OpenAI",
            "category": "Intelligence",
            "description": "Summarisation, prioritisation and drafting for every generated brief.",
            "metrics": [
                {"label": "Model", "value": "gpt-5.1"},
                {"label": "Briefs generated", "value": "128"},
            ],
            "poweredBy": "OpenAI Platform",
        },
    ),
    dict(
        provider="n8n",
        status="not-connected",
        account=None,
        scopes=["workflow.execute"],
        last_sync_at=None,
        connected_at=None,
        config={
            "name": "n8n",
            "category": "Automation",
            "description": "Scheduled brief generation and downstream workflow triggers.",
            "metrics": [
                {"label": "Workflows", "value": "0"},
                {"label": "Runs this month", "value": "0"},
            ],
            "poweredBy": "n8n Cloud",
        },
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)

        # Idempotent by provider: re-running the script after a partial seed
        # (or in CI) never creates duplicate integrations for the demo user.
        existing_providers = {
            provider
            for (provider,) in db.query(Integration.provider)
            .filter(Integration.user_id == user.id)
            .all()
        }

        seed_idempotently(
            db,
            model=Integration,
            user=user,
            items=INTEGRATIONS,
            existing_keys=existing_providers,
            key_fn=lambda integration: integration["provider"],
            label="integration(s)",
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
