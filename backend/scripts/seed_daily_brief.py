"""Seed one realistic DailyBrief row into PostgreSQL.

Usage (from backend/):

    python scripts/seed_daily_brief.py

Run this only after applying the Alembic migration for the `daily_briefs`
table. This script writes through `DailyBriefService.create_brief()` — the
same ORM model FastAPI uses at request time — so the live table must already
match `app.models.DailyBrief` or the insert will fail with a column error.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allows `python scripts/seed_daily_brief.py` to work without installing the
# package: put the backend root (this file's grandparent) on the path so
# `from app...` resolves the same way it does under uvicorn.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.services.daily_brief_service import DailyBriefService  # noqa: E402
from app.services.demo_user import get_or_create_demo_user  # noqa: E402

SUMMARY = (
    "Meridian Labs has gone quiet for nine days on a $480K renewal that closes Friday, and their "
    "champion forwarded a competitor's pricing sheet last night. That is the single decision that "
    "moves the quarter. Beyond it, the day is manageable: four meetings, two of which need real "
    "preparation, and six emails that genuinely need you rather than your team."
)

PRIORITIES = [
    {
        "id": "pri_1",
        "rank": 1,
        "title": "Decide the Meridian Labs renewal position before the 11:00 call",
        "detail": (
            "Nine days of silence, a competitor quote in the thread, and a Friday close date. "
            "You need a defended number and a walk-away line before you dial in."
        ),
        "urgency": "critical",
        "owner": "Lydia",
        "source": "GoHighLevel",
    },
    {
        "id": "pri_2",
        "rank": 2,
        "title": "Approve the engineering hiring plan to unblock the Q3 roadmap",
        "detail": "Recruiting has three finalists ready to close, but the plan has sat in review for four days.",
        "urgency": "high",
        "owner": "Lydia",
        "source": "Notion",
    },
]

RISKS = [
    {
        "id": "risk_1",
        "title": "Meridian Labs renewal is being competitively shopped",
        "detail": (
            "Their VP of Engineering forwarded a competitor pricing sheet at 22:14 last night, most "
            "likely by accident. The thread shows procurement is modelling a 30% reduction."
        ),
        "severity": "critical",
        "impact": "$480K ARR",
        "mitigation": "Lead with the migration cost analysis, not a discount. Hold price, extend term.",
        "source": "Gmail",
    },
]

RECOMMENDATIONS = [
    {
        "id": "rec_1",
        "title": "Send the Meridian migration-cost analysis before the 11:00 call",
        "rationale": "Reframes the conversation around switching cost instead of price.",
    },
    {
        "id": "rec_2",
        "title": "Approve the engineering hiring plan today",
        "rationale": "Every day of delay pushes the Q3 roadmap back by roughly a week.",
    },
]

EXECUTIVE_SCORE = 74


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)
        brief = DailyBriefService(db, user).create_brief(
            summary=SUMMARY,
            priorities=PRIORITIES,
            risks=RISKS,
            recommendations=RECOMMENDATIONS,
            executive_score=EXECUTIVE_SCORE,
            generated_at=datetime.now(timezone.utc),
        )
        print(f"Seeded DailyBrief {brief.id} (executive score {brief.executiveScore})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
