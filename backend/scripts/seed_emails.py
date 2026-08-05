"""Seed several realistic Email rows into PostgreSQL.

Usage (from backend/):

    python scripts/seed_emails.py

Run this only after applying the Alembic migration that creates the current
`emails` shape (category/subject/sender/ai_summary/priority/
suggested_response/reading_time/thread_count/unread/labels/received_at —
see `app.models.Email`). This script writes directly through the `Email`
ORM model rather than through a service method, because `InboxService` is
intentionally read-only: it only ever *retrieves* emails for the API (see
`InboxService.list_emails()`), so there is no write path to route through.
Emails need a `user_id`, so this script also finds or creates a demo user
matching `mock_data.USER`.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allows `python scripts/seed_emails.py` to work without installing the
# package: put the backend root (this file's grandparent) on the path so
# `from app...` resolves the same way it does under uvicorn, and put this
# file's own directory on the path so `seed_common` resolves too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Email  # noqa: E402
from seed_common import get_or_create_demo_user, seed_idempotently  # noqa: E402

# Matches mock_data.USER so seeded emails sit consistently alongside the
# rest of the mocked morning brief.
ATHENS = timezone(timedelta(hours=3))


def _at(month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=ATHENS)


EMAILS = [
    # Board communication
    dict(
        thread_id="thread_board_deck",
        category="needs-reply",
        subject="Board deck v3 — final numbers attached",
        sender={"name": "Sarah Chen", "email": "sarah@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "SC"},
        received_at=_at(8, 3, 21, 40),
        ai_summary=(
            "July actuals are finalised and the deck is otherwise ready. Your closing remarks slide "
            "is still a placeholder, and the board meeting is tomorrow morning."
        ),
        priority="high",
        suggested_response=(
            "Confirm you'll have the closing remarks slide done before 08:00 and flag if you want "
            "Sarah's help framing the Meridian narrative."
        ),
        reading_time="2 min",
        thread_count=3,
        unread=True,
        labels=["Board", "Finance"],
    ),
    # Investor update
    dict(
        thread_id="thread_investor_update",
        category="needs-reply",
        subject="Re: Monthly update — question on pipeline coverage",
        sender={"name": "Daniel Ostrow", "email": "daniel@vantagecapital.vc", "company": "Vantage Capital", "avatar": "DO"},
        received_at=_at(8, 3, 19, 5),
        ai_summary=(
            "Daniel read the July update and wants context on last month's dip in pipeline coverage "
            "before tomorrow's call. Straightforward to answer — coverage has already recovered to 3.4x."
        ),
        priority="medium",
        suggested_response=(
            "Reply that coverage recovered to 3.4x after two new enterprise opportunities opened, and "
            "that you'll walk through it live tomorrow."
        ),
        reading_time="1 min",
        thread_count=2,
        unread=True,
        labels=["Investor", "Vantage Capital"],
    ),
    # Customer request
    dict(
        thread_id="thread_globex_p1",
        category="high-priority",
        subject="P1 — export job failing since Tuesday",
        sender={"name": "Alicia Ferreira", "email": "alicia.ferreira@globexcorp.com", "company": "Globex Corp", "avatar": "AF"},
        received_at=_at(7, 29, 9, 12),
        ai_summary=(
            "Nightly export to Globex's warehouse has failed for six days and support has not closed "
            "the loop. Root cause is identified; this is now a relationship risk more than a technical one."
        ),
        priority="critical",
        suggested_response=(
            "Personally confirm the fix ships this week and offer a service credit before the Q4 "
            "renewal conversation starts."
        ),
        reading_time="2 min",
        thread_count=6,
        unread=True,
        labels=["Customer", "Support", "Globex Corp"],
    ),
    # Internal announcement
    dict(
        thread_id="thread_allhands",
        category="informational",
        subject="Engineering all-hands moved to Thursday 10:00",
        sender={"name": "Marcus Webb", "email": "marcus@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "MW"},
        received_at=_at(8, 3, 15, 0),
        ai_summary=(
            "Standing engineering all-hands moved from Wednesday to Thursday to avoid conflicting with "
            "the Pinnacle Health security review. No action needed."
        ),
        priority="low",
        suggested_response="No response required.",
        reading_time="1 min",
        thread_count=1,
        unread=False,
        labels=["Internal", "Announcement"],
    ),
    # Hiring / recruiting
    dict(
        thread_id="thread_hiring_jordan",
        category="needs-reply",
        subject="Jordan Wu — offer approval needed before Thursday",
        sender={"name": "Priya Shah", "email": "priya@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "PS"},
        received_at=_at(8, 4, 8, 30),
        ai_summary=(
            "Final panel feedback for Jordan Wu is in at 4.6/5 average. The offer needs to go out "
            "before Thursday or the requisition tied to the Q3 hiring plan expires."
        ),
        priority="high",
        suggested_response=(
            "Approve the offer and confirm compensation band, contingent on the hiring plan being "
            "signed off today."
        ),
        reading_time="1 min",
        thread_count=1,
        unread=True,
        labels=["Hiring", "Internal"],
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)

        # Idempotent by subject: re-running the script after a partial seed
        # (or in CI) never creates duplicate emails for the demo user.
        existing_subjects = {
            subject
            for (subject,) in db.query(Email.subject).filter(Email.user_id == user.id).all()
        }

        seed_idempotently(
            db,
            model=Email,
            user=user,
            items=EMAILS,
            existing_keys=existing_subjects,
            key_fn=lambda email: email["subject"],
            label="email(s)",
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
