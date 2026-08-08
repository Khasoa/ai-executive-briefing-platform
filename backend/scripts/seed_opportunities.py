"""Seed several realistic Opportunity rows into PostgreSQL.

Usage (from backend/):

    python scripts/seed_opportunities.py

Run this only after applying the Alembic migration that creates the current
`opportunities` shape (company/stage/value/probability/owner/close_date/
risk_level/last_interaction/ai_summary/recommended_action/signals — see
`app.models.Opportunity`). This script writes directly through the
`Opportunity` ORM model rather than through a service method, because
`CRMService` is intentionally read-only: it only ever *retrieves* the
pipeline for the API (see `CRMService.list_opportunities()`), so there is
no write path to route through. Opportunities need a `user_id`, so this
script also finds or creates a demo user matching `mock_data.USER`.
"""

import sys
from datetime import date
from pathlib import Path

# Allows `python scripts/seed_opportunities.py` to work without installing
# the package: put the backend root (this file's grandparent) on the path so
# `from app...` resolves the same way it does under uvicorn, and put this
# file's own directory on the path so `seed_common` resolves too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Opportunity  # noqa: E402
from seed_common import get_or_create_demo_user, seed_idempotently  # noqa: E402

OPPORTUNITIES = [
    # Enterprise SaaS renewal
    dict(
        company="Meridian Labs",
        logo="ML",
        industry="Industrial R&D software",
        stage="Renewal",
        value=480_000,
        probability=55,
        owner="Elena Park",
        close_date=date(2026, 8, 7),
        risk_level="critical",
        last_interaction={
            "type": "email",
            "summary": "Competitor pricing sheet forwarded by their champion",
            "time": "22:14 yesterday",
            "sources": ["GoHighLevel", "Gmail"],
        },
        ai_summary=(
            "A three-year customer at 94% utilisation is being competitively re-tendered by a new "
            "procurement lead. Probability dropped 25 points overnight when a competitor quote "
            "entered the thread. The champion relationship is intact; the risk is entirely commercial."
        ),
        recommended_action=(
            "Hold price and offer a 36-month term with a capped uplift. Bring the migration cost "
            "analysis to the 11:00 call."
        ),
        signals=["Champion still engaged", "94% utilisation", "New procurement lead", "Competitor in thread"],
    ),
    # New customer acquisition
    dict(
        company="Pinnacle Health",
        logo="PH",
        industry="Healthcare provider network",
        stage="Security Review",
        value=520_000,
        probability=65,
        owner="Elena Park",
        close_date=date(2026, 9, 12),
        risk_level="low",
        last_interaction={
            "type": "email",
            "summary": "One open questionnaire item before legal review",
            "time": "Yesterday, 16:40",
            "sources": ["GoHighLevel", "Gmail"],
        },
        ai_summary=(
            "New-business opportunity in final security review. Only one questionnaire item remains "
            "open, which engineering has already confirmed is supported, so this is close to signature."
        ),
        recommended_action="Answer item 4.7 in writing before the 14:00 call so legal can start this week.",
        signals=["Executive champion", "Budget confirmed", "Single open blocker"],
    ),
    # Expansion opportunity
    dict(
        company="Northwind Digital",
        logo="ND",
        industry="Digital agency network",
        stage="Expansion",
        value=110_000,
        probability=60,
        owner="Elena Park",
        close_date=date(2026, 10, 1),
        risk_level="medium",
        last_interaction={
            "type": "meeting",
            "summary": "QBR moved to 15:30 with two finance attendees added",
            "time": "Yesterday, 18:05",
            "sources": ["GoHighLevel", "Google Calendar"],
        },
        ai_summary=(
            "EMEA expansion worth roughly 140 seats on an existing account. The customer has raised it "
            "twice unprompted, and two finance-adjacent attendees were just added to today's QBR, which "
            "often precedes a budget conversation."
        ),
        recommended_action="Ask directly at the QBR who owns the EMEA budget and what approval requires.",
        signals=["Customer-initiated", "71% utilisation", "Finance joined late"],
    ),
    # Strategic partnership
    dict(
        company="Bridgepoint Research",
        logo="BR",
        industry="Industry research & analyst network",
        stage="Partnership",
        value=150_000,
        probability=40,
        owner="Lydia Reyes",
        close_date=date(2026, 11, 3),
        risk_level="medium",
        last_interaction={
            "type": "call",
            "summary": "Discussed a co-branded benchmark report and referral pipeline",
            "time": "3 days ago",
            "sources": ["Gmail"],
        },
        ai_summary=(
            "Proposed distribution partnership: Bridgepoint's benchmark reports would reference "
            "Arcadia as the enterprise SaaS case study, with a reciprocal referral arrangement. Still "
            "in scoping — no commercial terms exchanged yet."
        ),
        recommended_action="Send a one-page partnership scope so their legal team can start reviewing.",
        signals=["No formal terms yet", "Mutual introduction", "Analyst relationship"],
    ),
    # Upsell opportunity
    dict(
        company="Globex Corp",
        logo="GC",
        industry="Logistics software",
        stage="Upsell",
        value=95_000,
        probability=70,
        owner="Marcus Webb",
        close_date=date(2026, 8, 22),
        risk_level="low",
        last_interaction={
            "type": "support",
            "summary": "Reporting latency escalation resolved; asked about the analytics add-on",
            "time": "2 days ago",
            "sources": ["GoHighLevel", "Gmail"],
        },
        ai_summary=(
            "Existing customer asked about the advanced analytics add-on while a support escalation "
            "was being resolved — a good-faith moment right after a fast fix, not a fresh evaluation."
        ),
        recommended_action="Have Marcus follow up with an add-on quote while the resolution is still fresh.",
        signals=["Existing customer", "Inbound interest", "Recently resolved escalation"],
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)

        # Idempotent by company + stage: re-running the script after a
        # partial seed (or in CI) never creates duplicate opportunities for
        # the demo user.
        existing = {
            (company, stage)
            for (company, stage) in db.query(Opportunity.company, Opportunity.stage)
            .filter(Opportunity.user_id == user.id)
            .all()
        }

        seed_idempotently(
            db,
            model=Opportunity,
            user=user,
            items=OPPORTUNITIES,
            existing_keys=existing,
            key_fn=lambda opportunity: (opportunity["company"], opportunity["stage"]),
            describe_fn=lambda o: f"'{o['company']} — {o['stage']}'",
            label="opportunity(ies)",
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
