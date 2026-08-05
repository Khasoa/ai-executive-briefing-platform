"""Seed today's MorningBrief (and its checklist) into PostgreSQL.

Usage (from backend/):

    python scripts/seed_morning_brief.py

Run this only after applying the Alembic migration for the `morning_briefs`
and `brief_actions` tables (see `app.models.MorningBrief`,
`app.models.BriefAction`).

Unlike the other seed scripts, this does not build its own rows and hand
them to `seed_idempotently()` — `MorningBriefService.regenerate()` already
*is* the idempotent "create or replace today's brief" operation (see Phase 7
in `backend/README.md`): it looks up the demo user via
`app.services.demo_user.get_or_create_demo_user` (also what `seed_common`
re-exports for the other scripts), creates today's `MorningBrief` if one
doesn't exist yet, and never touches `BriefAction` rows that already exist.
Re-running this script is therefore always safe: it refreshes today's report
content and, the first time, seeds the checklist from `mock_data
.ACTION_CHECKLIST` — after that, it leaves checklist progress alone.
"""

import sys
from pathlib import Path

# Allows `python scripts/seed_morning_brief.py` to work without installing
# the package: put the backend root (this file's grandparent) on the path so
# `from app...` resolves the same way it does under uvicorn.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.services.morning_brief_service import MorningBriefService  # noqa: E402


def seed() -> None:
    db = SessionLocal()
    try:
        brief = MorningBriefService(db).regenerate()
        print(f"Seeded MorningBrief {brief.meta.id} for {brief.meta.date!r}")
        print(f"  headline: {brief.meta.headline!r}")
        print(f"  {len(brief.actionChecklist)} checklist item(s)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
