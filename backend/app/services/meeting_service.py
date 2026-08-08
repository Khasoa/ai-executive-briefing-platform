import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Meeting
from app.schemas.meetings import MeetingSchema, MeetingsResponse
from app.services import mock_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.mapping_utils import jsonb_or_default, stringify_id

logger = logging.getLogger("briefly.meetings")


class MeetingService:
    """Meeting intelligence: context and preparation rather than a calendar grid.

    Phase 2 of the PostgreSQL migration: meetings are read from the
    `meetings` table when rows exist there, falling back to
    `mock_data.MEETINGS` otherwise — including when the database itself is
    unreachable. See `list_meetings()` for the fallback mechanics.

    `list_meetings()` is public on purpose: it is the one place that knows
    how to load meetings, so any other service that needs meeting data
    (`OverviewService`, `MorningBriefService`, `WorkspaceService`) calls it
    instead of reading `mock_data.MEETINGS` directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_meetings(self) -> MeetingsResponse:
        meetings = self.list_meetings()
        return MeetingsResponse(
            date=mock_data.BRIEF_DATE,
            meetingCount=len(meetings),
            needsPreparation=sum(1 for m in meetings if m["prepStatus"] == "needs-prep"),
            totalScheduledMinutes=sum(self._minutes(m) for m in meetings),
            meetings=meetings,
        )

    def get_meeting(self, meeting_id: str) -> MeetingSchema:
        # Reuses `list_meetings()` rather than a dedicated lookup so a single
        # request never mixes a database-backed list with a mock-backed one:
        # whichever source answered `list_meetings()` is the only source
        # `get_meeting()` searches too.
        for meeting in self.list_meetings():
            if meeting["id"] == meeting_id:
                return MeetingSchema(**meeting)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting '{meeting_id}' not found",
        )

    def list_meetings(self) -> list[dict]:
        """Read every meeting from PostgreSQL, falling back to `mock_data.MEETINGS`.

        Fallback strategy: two situations land here — the table is reachable
        but empty (nothing seeded yet), or the database itself is unreachable
        (not migrated, connection dropped, credentials wrong). Both are
        treated the same way, because from the API's point of view they mean
        the same thing: there is nothing trustworthy in Postgres right now.
        An empty result is logged at info level (a normal, expected state
        before seeding); a database error is logged as a warning (something
        is actually wrong) — but either way we serve the curated meetings
        instead of returning an empty or broken response, so a database
        problem degrades this page rather than breaking it. The actual
        try/except and empty check live in `load_rows_with_fallback`, shared
        with `InboxService`, `CRMService` and `IntegrationService`.
        """
        return load_rows_with_fallback(
            query=lambda: self.db.query(Meeting).order_by(Meeting.starts_at.asc()).all(),
            to_dict=self._to_dict,
            fallback=mock_data.MEETINGS,
            logger=logger,
            label="meetings",
            db=self.db,
        )

    @staticmethod
    def _to_dict(meeting: Meeting) -> dict:
        """Map a `Meeting` row onto the exact dict shape `MeetingSchema` expects.

        `attendees`, `agenda`, `company` and `sources` map onto columns
        one-to-one. `relatedEmails`, `preparationNotes`, `talkingPoints`,
        `recommendedQuestions` and `risks` all live inside the single
        `intelligence` JSONB column — grouped there because they are all
        generated preparation rather than raw calendar data, so adding one
        more of them later never needs a schema change.
        """
        intelligence = jsonb_or_default(meeting.intelligence)
        return {
            "id": stringify_id(meeting.id),
            "title": meeting.title,
            "startTime": meeting.starts_at.strftime("%H:%M"),
            "endTime": meeting.ends_at.strftime("%H:%M"),
            "duration": MeetingService._format_duration(meeting.starts_at, meeting.ends_at),
            "type": meeting.type,
            "location": meeting.location,
            "prepStatus": meeting.prep_status,
            "prepReason": meeting.prep_reason,
            "attendees": meeting.attendees,
            "agenda": meeting.agenda,
            "company": meeting.company,
            "relatedEmails": intelligence.get("relatedEmails", []),
            "preparationNotes": intelligence.get("preparationNotes", []),
            "talkingPoints": intelligence.get("talkingPoints", []),
            "recommendedQuestions": intelligence.get("recommendedQuestions", []),
            "risks": intelligence.get("risks", []),
            "sources": meeting.sources,
        }

    @staticmethod
    def _format_duration(starts_at, ends_at) -> str:
        minutes = int((ends_at - starts_at).total_seconds() // 60)
        return f"{minutes} min"

    @staticmethod
    def _minutes(meeting: dict) -> int:
        start_hour, start_minute = (int(part) for part in meeting["startTime"].split(":"))
        end_hour, end_minute = (int(part) for part in meeting["endTime"].split(":"))
        return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
