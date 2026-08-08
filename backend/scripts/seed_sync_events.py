"""Seed SyncEvent audit rows for the demo integrations.

Usage (from backend/):

    python scripts/seed_sync_events.py

Run this after `seed_integrations.py` — every SyncEvent needs an
`integration_id` foreign key. Idempotent by (provider, event, detail):
re-running never creates duplicate history rows for the same demo events.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Integration, SyncEvent  # noqa: E402
from seed_common import get_or_create_demo_user  # noqa: E402

_NOW = datetime.now(timezone.utc)

# (provider, event, status, detail, minutes_ago)
EVENTS = [
    (
        "gohighlevel",
        "Incremental sync started",
        "running",
        "Pulling opportunity stage changes since 05:31",
        1,
    ),
    (
        "gmail",
        "Thread sync completed",
        "success",
        "24 threads, 11 new since yesterday",
        3,
    ),
    (
        "google-calendar",
        "Event sync completed",
        "success",
        "4 events today, 1 reschedule detected",
        4,
    ),
    (
        "notion",
        "Page index refreshed",
        "success",
        "12 pages, 2 updated overnight",
        42,
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)
        integrations = {
            row.provider: row
            for row in db.query(Integration).filter(Integration.user_id == user.id).all()
        }
        if not integrations:
            print("No integrations for the demo user — run seed_integrations.py first")
            return

        existing = {
            (event.integration.provider, event.event, event.detail)
            for event in (
                db.query(SyncEvent)
                .join(Integration)
                .filter(Integration.user_id == user.id)
                .all()
            )
        }

        created = 0
        for provider, event, status, detail, minutes_ago in EVENTS:
            integration = integrations.get(provider)
            if integration is None:
                print(f"Skipping {provider!r} — integration not seeded")
                continue
            key = (provider, event, detail)
            if key in existing:
                print(f"Skipping {provider}/{event!r} — already seeded")
                continue

            db.add(
                SyncEvent(
                    integration_id=integration.id,
                    event=event,
                    status=status,
                    detail=detail,
                    occurred_at=_NOW - timedelta(minutes=minutes_ago),
                )
            )
            created += 1

        db.commit()
        print(f"Seeded {created} sync event(s) for {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
