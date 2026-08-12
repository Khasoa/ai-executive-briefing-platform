import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Meeting, User
from app.schemas.meetings import MeetingSchema, MeetingsResponse, MeetingWindowsSchema
from app.services import demo_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.demo_user import is_demo_user
from app.services.mapping_utils import jsonb_or_default, stringify_id
from app.services.meeting_intelligence import MeetingIntelligenceService
from app.services.meeting_windows import (
    classify_meeting_at,
    format_local_date_label,
    prep_recommended_for_window,
    relative_meeting_label,
)

logger = logging.getLogger("briefly.meetings")


class MeetingService:
    """Meeting intelligence: context and preparation rather than a calendar grid.

    Timing windows (today / this week / this month / later / past) come from
    `MeetingIntelligenceService` so Overview, Morning Brief, and Digest share
    the same classification rules.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_meetings(self) -> MeetingsResponse:
        intel = MeetingIntelligenceService(self.db, self.user)
        classified = intel.load_classified_meetings(include_past=True)

        # Demo tenant: curated day surface when DB is empty or only has past rows
        # (stale seeded titles must not leave "0 today").
        upcoming = [m for m in classified if m.get("window") != "past"]
        if is_demo_user(self.user) and not upcoming:
            classified = [self._enrich_demo_meeting(m) for m in demo_data.MEETINGS]

        # Attach prep context: rich for today, light "not yet" for future windows.
        enriched: list[dict] = []
        for meeting in classified:
            ctx = intel.build_prep_context(meeting)
            meeting = {
                **meeting,
                "relatedEmails": ctx.get("relatedEmailMatches")
                or meeting.get("relatedEmails")
                or [],
                "relatedOpportunities": ctx.get("relatedOpportunities") or [],
                "relatedWorkItems": ctx.get("relatedWorkItems") or [],
                "whyItMatters": ctx.get("whyItMatters"),
                "suggestedPrepActions": ctx.get("suggestedPrepActions") or [],
                "prepHighlights": ctx.get("prepHighlights") or [],
                "prepStatusLabel": ctx.get("prepStatusLabel") or meeting.get("prepStatusLabel"),
                "contextNote": ctx.get("contextNote")
                or (ctx.get("contextAvailability") or {}).get("contextNote"),
            }
            enriched.append(meeting)

        today = [m for m in enriched if m.get("window") == "today"]
        needs_today = [m for m in today if m.get("prepRecommended")]
        # Flat list: today first, then forward windows, past last.
        ordered = (
            [m for m in enriched if m.get("window") == "today"]
            + [m for m in enriched if m.get("window") == "tomorrow"]
            + [m for m in enriched if m.get("window") == "this_week"]
            + [m for m in enriched if m.get("window") == "this_month"]
            + [m for m in enriched if m.get("window") == "later"]
            + [m for m in enriched if m.get("window") == "past"]
        )

        normalized = [self._normalize_for_schema(m) for m in ordered]
        groups = intel.group_by_window(enriched)
        windows = MeetingWindowsSchema(
            today=[self._normalize_for_schema(m) for m in (groups.get("today") or [])],
            tomorrow=[self._normalize_for_schema(m) for m in (groups.get("tomorrow") or [])],
            thisWeek=[self._normalize_for_schema(m) for m in (groups.get("this_week") or [])],
            thisMonth=[self._normalize_for_schema(m) for m in (groups.get("this_month") or [])],
            later=[self._normalize_for_schema(m) for m in (groups.get("later") or [])],
            past=[self._normalize_for_schema(m) for m in (groups.get("past") or [])],
        )

        return MeetingsResponse(
            date=format_local_date_label(self.user),
            meetingCount=len(today),
            needsPreparation=len(needs_today),
            totalScheduledMinutes=sum(self._minutes(m) for m in today),
            meetings=normalized,
            todayCount=len(today),
            needsPreparationToday=len(needs_today),
            windows=windows,
        )

    def get_meeting(self, meeting_id: str) -> MeetingSchema:
        self._maybe_enrich_meeting(meeting_id)
        intel = MeetingIntelligenceService(self.db, self.user)
        for meeting in intel.load_classified_meetings(include_past=True):
            if meeting["id"] == meeting_id:
                ctx = intel.build_prep_context(meeting)
                meeting = {
                    **meeting,
                    "relatedEmails": ctx.get("relatedEmailMatches")
                    or meeting.get("relatedEmails")
                    or [],
                    "relatedOpportunities": ctx.get("relatedOpportunities") or [],
                    "relatedWorkItems": ctx.get("relatedWorkItems") or [],
                    "whyItMatters": ctx.get("whyItMatters"),
                    "suggestedPrepActions": ctx.get("suggestedPrepActions") or [],
                    "prepHighlights": ctx.get("prepHighlights") or [],
                    "prepStatusLabel": ctx.get("prepStatusLabel") or meeting.get("prepStatusLabel"),
                    "contextNote": ctx.get("contextNote")
                    or (ctx.get("contextAvailability") or {}).get("contextNote"),
                }
                return MeetingSchema(**self._normalize_for_schema(meeting))

        # Demo fallback ids.
        for meeting in self.list_meetings():
            if meeting["id"] == meeting_id:
                return MeetingSchema(**self._normalize_for_schema(meeting))

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting '{meeting_id}' not found",
        )

    def list_meetings(self) -> list[dict]:
        """Read every meeting from PostgreSQL, falling back to `demo_data.MEETINGS`."""
        intel = MeetingIntelligenceService(self.db, self.user)
        classified = intel.load_classified_meetings(include_past=True)
        upcoming = [m for m in classified if m.get("window") != "past"]
        if is_demo_user(self.user) and not upcoming:
            return [self._enrich_demo_meeting(m) for m in demo_data.MEETINGS]
        if classified:
            return classified

        fallback = demo_data.MEETINGS if is_demo_user(self.user) else []
        if fallback:
            return [self._enrich_demo_meeting(m) for m in fallback]

        return load_rows_with_fallback(
            query=lambda: (
                self.db.query(Meeting)
                .filter(Meeting.user_id == self.user.id)
                .order_by(Meeting.starts_at.asc())
                .all()
            ),
            to_dict=self._to_dict,
            fallback=[],
            logger=logger,
            label="meetings",
            db=self.db,
        )

    def _enrich_demo_meeting(self, meeting: dict) -> dict:
        """Mark curated demo meetings as today so demo UX stays coherent."""
        enriched = dict(meeting)
        enriched.setdefault("window", "today")
        enriched.setdefault("startsAt", None)
        enriched.setdefault("endsAt", None)
        enriched.setdefault("relativeLabel", "Today")
        enriched.setdefault("timingLabel", "Today")
        enriched.setdefault("dateLabel", "")
        enriched.setdefault("weekdayDateLabel", "")
        enriched["prepRecommended"] = prep_recommended_for_window(
            "today", enriched.get("prepStatus")
        )
        enriched.setdefault("prepStatusLabel", "Prepare today" if enriched["prepRecommended"] else "Ready")
        return enriched

    @staticmethod
    def _normalize_for_schema(meeting: dict) -> dict:
        from app.services.agenda_sanitize import sanitize_agenda

        company = meeting.get("company") or {}
        if not isinstance(company, dict):
            company = {}
        # Ensure required company keys exist for MeetingCompanySchema.
        company = {
            "name": company.get("name") or "",
            "industry": company.get("industry") or "",
            "size": company.get("size") or "",
            "relationship": company.get("relationship") or "",
            "background": company.get("background") or "",
            "arr": company.get("arr"),
        }
        attendees = []
        for attendee in meeting.get("attendees") or []:
            if not isinstance(attendee, dict):
                continue
            attendees.append(
                {
                    "name": attendee.get("name") or "Guest",
                    "role": attendee.get("role") or "",
                    "company": attendee.get("company") or "",
                    "avatar": attendee.get("avatar")
                    or "".join(p[0] for p in (attendee.get("name") or "G").split()[:2]).upper(),
                    "email": attendee.get("email"),
                }
            )
        meeting_type = meeting.get("type") or "internal"
        if meeting_type not in ("internal", "client", "investor", "personal"):
            meeting_type = "internal"
        organizer = meeting.get("organizer")
        if organizer and not isinstance(organizer, dict):
            organizer = None
        return {
            **meeting,
            "company": company,
            "attendees": attendees,
            "organizer": organizer,
            "type": meeting_type,
            "agenda": sanitize_agenda(meeting.get("agenda") or []),
            "relatedEmails": meeting.get("relatedEmails") or [],
            "preparationNotes": meeting.get("preparationNotes") or [],
            "talkingPoints": meeting.get("talkingPoints") or [],
            "recommendedQuestions": meeting.get("recommendedQuestions") or [],
            "risks": meeting.get("risks") or [],
            "sources": meeting.get("sources") or [],
            "suggestedPrepActions": meeting.get("suggestedPrepActions") or [],
            "prepHighlights": meeting.get("prepHighlights") or [],
            "relatedOpportunities": meeting.get("relatedOpportunities") or [],
            "relatedWorkItems": meeting.get("relatedWorkItems") or [],
            "isRecurring": bool(meeting.get("isRecurring")),
            "meetingLink": meeting.get("meetingLink") or None,
        }

    def _maybe_enrich_meeting(self, meeting_id: str) -> None:
        """Fill empty `intelligence` via AIService; never overwrite existing prep."""
        try:
            meeting_uuid = uuid.UUID(meeting_id)
        except ValueError:
            return

        try:
            row = (
                self.db.query(Meeting)
                .filter(Meeting.id == meeting_uuid, Meeting.user_id == self.user.id)
                .first()
            )
        except SQLAlchemyError:
            logger.warning("Could not load meeting for AI prep", exc_info=True)
            return

        if row is None:
            return

        # Only run expensive AI prep for today's meetings by default.
        if classify_meeting_at(row.starts_at, self.user) != "today":
            return

        intelligence = jsonb_or_default(row.intelligence)
        if self._intelligence_locked(intelligence):
            return

        from app.services.ai_service import AIService
        from app.services.crm_service import CRMService
        from app.services.inbox_service import InboxService

        company = jsonb_or_default(row.company)
        company_name = (company.get("name") or "").strip().lower()
        emails = InboxService(self.db, self.user).list_emails()
        related = []
        for email in emails[:30]:
            sender = email.get("sender") or {}
            hay = " ".join(
                [
                    email.get("subject") or "",
                    sender.get("name") or "",
                    sender.get("email") or "",
                ]
            ).lower()
            if company_name and company_name in hay:
                related.append(
                    {
                        "id": email["id"],
                        "subject": email["subject"],
                        "sender": sender.get("name") or "",
                        "summary": email.get("aiSummary") or "",
                        "time": email.get("timeLabel") or "",
                    }
                )
            if len(related) >= 5:
                break

        opportunities = CRMService(self.db, self.user).list_opportunities()
        crm_context = [
            o
            for o in opportunities
            if company_name and company_name in (o.get("company") or "").lower()
        ][:3]

        prep = AIService(self.db, self.user).generate_meeting_prep(
            {
                "title": row.title,
                "agenda": row.agenda or [],
                "participants": row.attendees or [],
                "company": company,
                "crm": crm_context,
                "recentEmails": related,
                "calendar": {
                    "startsAt": row.starts_at.isoformat() if row.starts_at else None,
                    "endsAt": row.ends_at.isoformat() if row.ends_at else None,
                    "type": row.type,
                    "location": row.location,
                    "prepStatus": row.prep_status,
                    "sources": row.sources or [],
                    "window": classify_meeting_at(row.starts_at, self.user),
                    "relativeLabel": relative_meeting_label(row.starts_at, self.user),
                },
            }
        )
        if prep is None:
            return

        related_emails = intelligence.get("relatedEmails") or related
        row.intelligence = {
            **intelligence,
            "relatedEmails": related_emails,
            "preparationNotes": prep["preparationNotes"],
            "talkingPoints": prep["talkingPoints"],
            "recommendedQuestions": prep["recommendedQuestions"],
            "risks": prep["risks"],
            "aiGenerated": True,
            "manuallyEdited": False,
        }
        if prep.get("prepReason"):
            row.prep_reason = prep["prepReason"]
        if row.prep_status == "needs-prep":
            row.prep_status = "ready"
        sources = list(row.sources or [])
        if "OpenAI" not in sources:
            sources.append("OpenAI")
            row.sources = sources
        try:
            self.db.commit()
        except SQLAlchemyError:
            logger.warning("Could not persist meeting AI prep", exc_info=True)
            self.db.rollback()

    @staticmethod
    def _intelligence_locked(intelligence: dict) -> bool:
        if intelligence.get("manuallyEdited"):
            return True
        return bool(
            intelligence.get("preparationNotes")
            or intelligence.get("talkingPoints")
            or intelligence.get("recommendedQuestions")
            or intelligence.get("risks")
        )

    def _to_dict(self, meeting: Meeting) -> dict:
        """Map a `Meeting` row onto the MeetingSchema-compatible dict."""
        return MeetingIntelligenceService(self.db, self.user).enrich_meeting_row(meeting)

    @staticmethod
    def _minutes(meeting: dict) -> int:
        start = meeting.get("startTime") or "0:0"
        end = meeting.get("endTime") or "0:0"
        try:
            start_hour, start_minute = (int(part) for part in start.split(":"))
            end_hour, end_minute = (int(part) for part in end.split(":"))
        except ValueError:
            return 0
        return max(0, (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute))
