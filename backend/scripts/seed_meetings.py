"""Seed several realistic Meeting rows into PostgreSQL.

Usage (from backend/):

    python scripts/seed_meetings.py

Run this only after applying the Alembic migration that creates the current
`meetings` shape (starts_at/ends_at/prep_status/prep_reason/attendees/agenda/
company/intelligence/sources — see `app.models.Meeting`). This script writes
directly through the `Meeting` ORM model rather than through a service
method, because `MeetingService` is intentionally read-only: it only ever
*retrieves* meetings for the API (see `MeetingService.list_meetings()`), so
there is no write path to route through. Meetings need a `user_id`, so this
script also finds or creates a demo user matching `mock_data.USER`.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allows `python scripts/seed_meetings.py` to work without installing the
# package: put the backend root (this file's grandparent) on the path so
# `from app...` resolves the same way it does under uvicorn, and put this
# file's own directory on the path so `seed_common` resolves too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Meeting  # noqa: E402
from seed_common import get_or_create_demo_user, seed_idempotently  # noqa: E402

# Matches mock_data.USER / mock_data.BRIEF_DATE so seeded meetings sit
# consistently alongside the rest of the mocked morning brief.
ATHENS = timezone(timedelta(hours=3))
MEETING_DATE = (2026, 8, 4)


def _at(hour: int, minute: int) -> datetime:
    year, month, day = MEETING_DATE
    return datetime(year, month, day, hour, minute, tzinfo=ATHENS)


MEETINGS = [
    dict(
        title="Board Meeting",
        starts_at=_at(8, 0),
        ends_at=_at(9, 0),
        type="internal",
        location="Boardroom A",
        prep_status="needs-prep",
        prep_reason="Closing remarks on the Meridian renewal are still unwritten.",
        attendees=[
            {"name": "Daniel Ostrow", "role": "Board Chair", "company": "Vantage Capital", "avatar": "DO"},
            {"name": "Priya Nair", "role": "Independent Director", "company": "Board Member", "avatar": "PN"},
            {"name": "Sarah Chen", "role": "CFO", "company": "Arcadia Systems", "avatar": "SC"},
        ],
        agenda=[
            "Q2 financial results and Q3 forecast",
            "Meridian Labs renewal and competitive exposure",
            "Fundraising timeline for the Series B",
            "Q3 hiring plan approval",
        ],
        company={
            "name": "Arcadia Systems — Board",
            "industry": "Governance",
            "size": "5 board members",
            "relationship": "Quarterly board meeting",
            "background": (
                "Second board meeting since the Series A. Daniel has asked twice for a clearer "
                "narrative on customer concentration risk given Meridian is 11% of ARR."
            ),
        },
        intelligence={
            "relatedEmails": [
                {
                    "id": "rel_board_1",
                    "subject": "Board deck v3 — final numbers attached",
                    "sender": "Sarah Chen",
                    "summary": "July actuals are in. Only your closing remarks slide is still a placeholder.",
                    "time": "Yesterday, 21:40",
                }
            ],
            "preparationNotes": [
                "Sarah's deck is final except your closing remarks slide — write it before 08:00.",
                "Daniel will ask about Meridian directly; have the renewal position ready before this call.",
            ],
            "talkingPoints": [
                "July NRR of 118% is the strongest data point against the concentration-risk narrative.",
                "Series B outreach begins once the Meridian renewal closes, not before.",
                "Hiring plan approval unblocks two staff engineering offers expiring Thursday.",
            ],
            "recommendedQuestions": [
                "What would the board need to see to be comfortable accelerating the raise timeline?",
            ],
            "risks": [
                {
                    "title": "Customer concentration question resurfaces",
                    "detail": "Meridian at 11% of ARR is now a recurring board concern, not a one-off.",
                    "severity": "medium",
                }
            ],
        },
        sources=["Notion", "Google Calendar"],
    ),
    dict(
        title="Investor Update — Vantage Capital",
        starts_at=_at(10, 0),
        ends_at=_at(10, 30),
        type="investor",
        location="Zoom",
        prep_status="ready",
        prep_reason="Monthly update deck was sent Monday; no open questions from Daniel yet.",
        attendees=[
            {"name": "Daniel Ostrow", "role": "Partner", "company": "Vantage Capital", "avatar": "DO"},
        ],
        agenda=[
            "Monthly metrics review",
            "Series B timeline",
            "Key hire updates",
        ],
        company={
            "name": "Vantage Capital",
            "industry": "Venture capital",
            "size": "Lead investor, Series A",
            "relationship": "Board seat since Series A",
            "background": (
                "Daniel leads the board seat and receives a monthly async update; this is the live "
                "follow-up call he requested after last month's dip in pipeline coverage."
            ),
        },
        intelligence={
            "relatedEmails": [
                {
                    "id": "rel_investor_1",
                    "subject": "Monthly update — July",
                    "sender": "Lydia Reyes",
                    "summary": "Sent Monday. Covers ARR, NRR, burn multiple and the Meridian renewal risk.",
                    "time": "2 days ago",
                }
            ],
            "preparationNotes": [
                "No written follow-up questions came back on the July update — expect this to run short.",
            ],
            "talkingPoints": [
                "Pipeline coverage recovered to 3.4x after two new enterprise opportunities opened.",
                "Series B conversations will start once Meridian's renewal is signed, not before.",
            ],
            "recommendedQuestions": [
                "Which two investors should we prioritise for early Series B conversations?",
            ],
            "risks": [],
        },
        sources=["Gmail", "Google Calendar"],
    ),
    dict(
        title="Customer Success Review — Globex Corp",
        starts_at=_at(12, 0),
        ends_at=_at(12, 45),
        type="client",
        location="Google Meet",
        prep_status="needs-prep",
        prep_reason="Support escalation from last week needs a resolution update before the call.",
        attendees=[
            {"name": "Alicia Ferreira", "role": "Head of Operations", "company": "Globex Corp", "avatar": "AF"},
            {"name": "Elena Park", "role": "VP Revenue", "company": "Arcadia Systems", "avatar": "EP"},
        ],
        agenda=[
            "Open support escalation review",
            "H1 usage and adoption trends",
            "Q4 renewal benchmarking against Meridian pricing",
        ],
        company={
            "name": "Globex Corp",
            "industry": "Logistics software",
            "size": "2,100 employees",
            "relationship": "Customer since January 2024",
            "arr": "$310K",
            "background": (
                "Globex renews in Q4 and is known to benchmark pricing against Meridian's contract. "
                "A P1 support ticket opened six days ago is still open, which is unusual for this account."
            ),
        },
        intelligence={
            "relatedEmails": [
                {
                    "id": "rel_cs_1",
                    "subject": "P1 — export job failing since Tuesday",
                    "sender": "Alicia Ferreira",
                    "summary": "Nightly export to their warehouse has failed for six days; support has not closed the loop.",
                    "time": "6 days ago",
                }
            ],
            "preparationNotes": [
                "Confirm the export bug fix is deployed before the call — do not promise a date you don't have.",
                "Alicia has not escalated publicly yet, but six days open on a P1 is past their patience.",
            ],
            "talkingPoints": [
                "Root cause identified as a schema change on their side; fix ships this week.",
                "Usage is up 22% quarter over quarter across their three business units.",
            ],
            "recommendedQuestions": [
                "Would a service credit resolve this, or is the relationship risk bigger than that?",
            ],
            "risks": [
                {
                    "title": "Open P1 undermines the Q4 renewal conversation",
                    "detail": "Globex explicitly benchmarks reliability against Meridian's contract terms.",
                    "severity": "high",
                }
            ],
        },
        sources=["Gmail", "Google Calendar", "GoHighLevel"],
    ),
    dict(
        title="Product Roadmap — Q4 Planning",
        starts_at=_at(14, 30),
        ends_at=_at(15, 30),
        type="internal",
        location="Google Meet",
        prep_status="ready",
        prep_reason="Marcus circulated the roadmap draft Friday; review before the call.",
        attendees=[
            {"name": "Marcus Webb", "role": "VP Engineering", "company": "Arcadia Systems", "avatar": "MW"},
            {"name": "Elena Park", "role": "VP Revenue", "company": "Arcadia Systems", "avatar": "EP"},
            {"name": "Sarah Chen", "role": "CFO", "company": "Arcadia Systems", "avatar": "SC"},
        ],
        agenda=[
            "Q4 roadmap prioritisation",
            "Engineering capacity given the open hiring plan",
            "Analytics module migration tooling for renewals like Meridian",
        ],
        company={
            "name": "Arcadia Systems",
            "industry": "Internal",
            "size": "64 employees",
            "relationship": "Leadership team",
            "background": (
                "Draft roadmap assumes both open staff engineering roles are filled by mid-Q4; the "
                "hiring plan approval today directly affects what is realistic to commit to."
            ),
        },
        intelligence={
            "relatedEmails": [
                {
                    "id": "rel_roadmap_1",
                    "subject": "Q4 roadmap draft v2",
                    "sender": "Marcus Webb",
                    "summary": "Circulated Friday. Flags migration tooling as the biggest open scope question.",
                    "time": "4 days ago",
                }
            ],
            "preparationNotes": [
                "Migration tooling investment ties directly to renewal defensibility — connect it to Meridian.",
            ],
            "talkingPoints": [
                "If the hiring plan is approved today, both roles could be filled by mid-Q4.",
                "Migration tooling would cut the Meridian-style migration estimate from seven months to three.",
            ],
            "recommendedQuestions": [
                "What is the roadmap fallback if only one of the two hires closes this quarter?",
            ],
            "risks": [
                {
                    "title": "Roadmap assumes hires that are not yet approved",
                    "detail": "Committing today ahead of the hiring plan decision would be premature.",
                    "severity": "medium",
                }
            ],
        },
        sources=["Notion", "Google Calendar"],
    ),
    dict(
        title="Hiring Interview — Staff Software Engineer",
        starts_at=_at(16, 30),
        ends_at=_at(17, 15),
        type="personal",
        location="Google Meet",
        prep_status="ready",
        prep_reason="Recruiting shared the candidate packet Monday; loop feedback is already positive.",
        attendees=[
            {
                "name": "Jordan Wu",
                "role": "Candidate — Staff Software Engineer",
                "company": "External Candidate",
                "avatar": "JW",
            },
            {"name": "Marcus Webb", "role": "VP Engineering", "company": "Arcadia Systems", "avatar": "MW"},
        ],
        agenda=[
            "Systems design walkthrough",
            "Leadership and mentorship track record",
            "Offer timeline given the Q3 hiring plan",
        ],
        company={
            "name": "Candidate — Jordan Wu",
            "industry": "Currently Staff Engineer at a Series C infrastructure company",
            "size": "Individual candidate",
            "relationship": "Final-round interview, offer stage",
            "background": (
                "Fourth and final interview. Two prior panels rated Jordan strongly on systems design "
                "and API architecture. This offer is one of the two blocked on today's hiring plan approval."
            ),
        },
        intelligence={
            "relatedEmails": [
                {
                    "id": "rel_hire_1",
                    "subject": "Jordan Wu — panel feedback (4.6/5 average)",
                    "sender": "Marcus Webb",
                    "summary": "All three prior interviewers recommend hiring; this is the closing conversation.",
                    "time": "2 days ago",
                }
            ],
            "preparationNotes": [
                "This is a closing conversation, not another evaluation round — sell the mission and the role.",
                "Offer depends on the hiring plan approval landing before Thursday's expiry.",
            ],
            "talkingPoints": [
                "Panel feedback has been consistently strong across all three prior rounds.",
                "Framing: this is the team that will own the migration tooling investment discussed today.",
            ],
            "recommendedQuestions": [
                "What would make another offer more attractive to Jordan than ours right now?",
            ],
            "risks": [
                {
                    "title": "Offer expires if the hiring plan isn't approved today",
                    "detail": "Recruiting has said the requisition must be open by Thursday to hold the offer.",
                    "severity": "high",
                }
            ],
        },
        sources=["Notion", "Gmail"],
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)

        # Idempotent by title: re-running the script after a partial seed
        # (or in CI) never creates duplicate meetings for the demo user.
        existing_titles = {
            title for (title,) in db.query(Meeting.title).filter(Meeting.user_id == user.id).all()
        }

        seed_idempotently(
            db,
            model=Meeting,
            user=user,
            items=MEETINGS,
            existing_keys=existing_titles,
            key_fn=lambda meeting: meeting["title"],
            label="meeting(s)",
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
