import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import BriefAction, MorningBrief, User
from app.schemas.morning_brief import ChecklistItemSchema, MorningBriefResponse
from app.services import demo_data
from app.services.db_fallback import read_with_fallback
from app.services.demo_user import public_user_dict
from app.services.inbox_service import InboxService
from app.services.mapping_utils import jsonb_or_default, relative_time_label, stringify_id
from app.services.meeting_service import MeetingService

logger = logging.getLogger("briefly.morning_brief")

# Emails promoted into the brief, in the order an executive should read them.
_BRIEF_EMAIL_IDS = ("em_1", "em_2", "em_3", "em_5", "em_4", "em_6")


class MorningBriefService:
    """Produces the Morning Brief — the product's primary output.

    Phase 7 of the PostgreSQL migration. `MorningBrief` (the report:
    headline, executive summary, priorities, risks, clients, suggested
    focus, delegation, closing answer) and `BriefAction` (the checklist)
    are read from and written to PostgreSQL for today's brief. `meetings`
    and `importantEmails` stay out of `MorningBrief` on purpose — they are
    pulled live from `MeetingService`/`InboxService` on every call (as
    Phase 6 already wired up), so the brief never shows a meeting or email
    that has since changed elsewhere.

    Fallback strategy, extending the pattern from `MeetingService`,
    `InboxService`, `CRMService` and `IntegrationService`: if PostgreSQL has
    no row for today (empty) or is unreachable, this generates the brief
    from `demo_data` and tries to persist it, so the *next* request finds a
    real row instead of regenerating every time. If that persistence
    attempt also fails — most likely because `morning_briefs`/
    `brief_actions` do not exist in the connected database yet — every
    method here falls all the way back to the exact pre-migration
    behaviour (`_mock_only_response()`, mutating `demo_data.ACTION_CHECKLIST`
    directly), so the feature keeps working today and starts persisting
    for real the moment those tables are migrated.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_brief(self) -> MorningBriefResponse:
        brief, actions = self._load_or_generate_brief()
        if brief is None:
            return self._mock_only_response()
        return self._to_response(brief, actions)

    def get_brief_meta(self) -> dict:
        """Freshness metadata for `/workspace` and `/overview`.

        Read-only against today's row — unlike `get_brief()`, this never
        generate-and-persists, so loading the shell does not create a brief
        as a side effect. Falls back to `demo_data.BRIEF_META` when no row
        exists or PostgreSQL is unreachable.
        """
        brief = read_with_fallback(
            read=self._read_todays_brief,
            fallback=None,
            logger=logger,
            label="morning_briefs",
            db=self.db,
            log_empty=False,
        )
        if brief is None:
            return demo_data.BRIEF_META
        return {
            "id": stringify_id(brief.id),
            "date": self._format_brief_date(brief.brief_date),
            "generatedAt": brief.generated_at.isoformat(),
            "generatedLabel": relative_time_label(brief.generated_at),
            "confidence": brief.confidence,
            "sources": brief.sources,
            "headline": brief.headline,
        }

    def regenerate(self) -> MorningBriefResponse:
        """Create or replace today's `MorningBrief` from the current generator.

        Only the mock-sourced generator moves today — see
        `_generated_content()` — once real integrations and OpenAI
        generation exist, this method re-runs that pipeline instead
        without any other change to the flow below it. Existing
        `BriefAction` rows for today are never recreated here, so
        regenerating the report never rewinds checklist progress the
        executive already made.
        """
        brief, actions = self._generate_and_persist()
        if brief is None:
            # Persistence isn't available — fall back to the pre-migration
            # behaviour of refreshing `demo_data.BRIEF_META` in place.
            demo_data.BRIEF_META["generatedAt"] = datetime.now(timezone.utc).isoformat()
            demo_data.BRIEF_META["generatedLabel"] = "just now"
            return self._mock_only_response()
        return self._to_response(brief, actions)

    def set_checklist_item(self, item_id: str, done: bool) -> ChecklistItemSchema:
        action = self._find_persisted_action(item_id)
        if action is not None:
            action.done = done
            action.completed_at = datetime.now(timezone.utc) if done else None
            self.db.commit()
            self.db.refresh(action)
            return self._action_to_schema(action)

        # No persisted match — either this id was never written to
        # PostgreSQL (persistence isn't available yet) or it is one of the
        # stable `demo_data.ACTION_CHECKLIST` ids `_mock_only_response()`
        # hands out in that situation. Mutating it in place matches the
        # pre-migration behaviour exactly.
        for item in demo_data.ACTION_CHECKLIST:
            if item["id"] == item_id:
                item["done"] = done
                return ChecklistItemSchema(**item)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item '{item_id}' not found",
        )

    # -- reading ---------------------------------------------------------

    def _load_or_generate_brief(self) -> tuple[MorningBrief | None, list[BriefAction] | None]:
        """Read today's brief from PostgreSQL, or generate-and-persist one.

        `read_with_fallback` covers the same two situations as the other
        migrated services: no row for today yet (empty), or the database is
        unreachable. Either way, `brief` comes back `None` and this method
        immediately tries to generate and persist today's brief from
        `demo_data` instead of just returning mock content — the one
        difference from a normal read-fallback, so the next request has a
        real row to read.
        """
        brief = read_with_fallback(
            read=self._read_todays_brief,
            fallback=None,
            logger=logger,
            label="morning_briefs",
            db=self.db,
        )
        if brief is not None:
            try:
                actions = self.db.query(BriefAction).filter(BriefAction.brief_id == brief.id).all()
            except SQLAlchemyError:
                actions = []
            return brief, actions

        return self._generate_and_persist()

    def _read_todays_brief(self) -> MorningBrief | None:
        return (
            self.db.query(MorningBrief)
            .filter(
                MorningBrief.user_id == self.user.id,
                MorningBrief.brief_date == date.today(),
            )
            .order_by(MorningBrief.generated_at.desc())
            .first()
        )

    def _find_persisted_action(self, item_id: str) -> BriefAction | None:
        try:
            action_id = uuid.UUID(item_id)
        except ValueError:
            return None

        try:
            return self.db.query(BriefAction).filter(BriefAction.id == action_id).first()
        except SQLAlchemyError:
            logger.warning(
                "Could not read brief_actions — falling back to demo_data", exc_info=True
            )
            return None

    # -- writing ----------------------------------------------------------

    def _generate_and_persist(self) -> tuple[MorningBrief | None, list[BriefAction] | None]:
        try:
            return self._write_brief(self._generated_content())
        except SQLAlchemyError:
            logger.warning(
                "Could not persist a generated morning brief — falling back to demo_data",
                exc_info=True,
            )
            self.db.rollback()
            return None, None

    def _write_brief(self, content: dict) -> tuple[MorningBrief, list[BriefAction]]:
        """Create or replace today's `MorningBrief` row from `content`.

        `BriefAction` rows are only ever inserted the first time a brief is
        generated for a given day — if today's brief already has a
        checklist, it is left untouched (see `regenerate()`).
        """
        today = date.today()

        brief = (
            self.db.query(MorningBrief)
            .filter(
                MorningBrief.user_id == self.user.id,
                MorningBrief.brief_date == today,
            )
            .first()
        )
        if brief is None:
            brief = MorningBrief(user_id=self.user.id, brief_date=today)
            self.db.add(brief)

        brief.headline = content["headline"]
        brief.executive_summary = content["executive_summary"]
        brief.confidence = content["confidence"]
        brief.sources = content["sources"]
        brief.sections = content["sections"]
        brief.closing = content["closing"]
        brief.generated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(brief)

        actions = self.db.query(BriefAction).filter(BriefAction.brief_id == brief.id).all()
        if not actions:
            actions = [BriefAction(brief_id=brief.id, **item) for item in content["checklist"]]
            self.db.add_all(actions)
            self.db.commit()
            for action in actions:
                self.db.refresh(action)

        return brief, actions

    @staticmethod
    def _generated_content() -> dict:
        """The mock-sourced "generator" for a brief's report content.

        Stands in for real generation (OpenAI, per the roadmap) — see
        `regenerate()`. Every value here is already shaped exactly like the
        JSONB columns on `MorningBrief` expect, so persisting it is a
        straight assignment with no transformation.
        """
        return {
            "headline": demo_data.BRIEF_META["headline"],
            "executive_summary": demo_data.EXECUTIVE_SUMMARY_TEXT,
            "confidence": demo_data.BRIEF_META["confidence"],
            "sources": demo_data.BRIEF_META["sources"],
            "sections": {
                "priorities": demo_data.PRIORITIES,
                "risks": demo_data.RISKS,
                "clients": demo_data.CLIENTS_NEEDING_ATTENTION,
                "focus": demo_data.SUGGESTED_FOCUS,
                "delegation": demo_data.RECOMMENDED_DELEGATION,
            },
            "closing": demo_data.CLOSING_ANSWER,
            "checklist": [
                {
                    "label": item["label"],
                    "category": item["category"],
                    "due": item["due"],
                    "done": item["done"],
                }
                for item in demo_data.ACTION_CHECKLIST
            ],
        }

    # -- mapping ----------------------------------------------------------

    def _to_response(self, brief: MorningBrief, actions: list[BriefAction]) -> MorningBriefResponse:
        sections = jsonb_or_default(brief.sections)

        return MorningBriefResponse(
            meta={
                "id": stringify_id(brief.id),
                "date": self._format_brief_date(brief.brief_date),
                "generatedAt": brief.generated_at.isoformat(),
                "generatedLabel": relative_time_label(brief.generated_at),
                "confidence": brief.confidence,
                "sources": brief.sources,
                "headline": brief.headline,
            },
            preparedFor=public_user_dict(self.user),
            executiveSummary=brief.executive_summary,
            topPriorities=sections.get("priorities", []),
            criticalRisks=sections.get("risks", []),
            meetings=self._meetings(),
            clientsNeedingAttention=sections.get("clients", []),
            importantEmails=self._important_emails(),
            suggestedFocus=sections.get("focus", {}),
            recommendedDelegation=sections.get("delegation", []),
            actionChecklist=[self._action_to_schema(action) for action in actions],
            closing=jsonb_or_default(brief.closing),
        )

    @staticmethod
    def _format_brief_date(brief_date: date) -> str:
        # Manual formatting (not `%-d`) to keep the day-of-month without a
        # leading zero on every platform, matching `demo_data.BRIEF_DATE`.
        return f"{brief_date.strftime('%A, %B')} {brief_date.day}, {brief_date.year}"

    @staticmethod
    def _action_to_schema(action: BriefAction) -> ChecklistItemSchema:
        return ChecklistItemSchema(
            id=stringify_id(action.id),
            label=action.label,
            category=action.category,
            due=action.due,
            done=action.done,
        )

    def _mock_only_response(self) -> MorningBriefResponse:
        """The pre-migration behaviour: every section straight from `demo_data`.

        Used when PostgreSQL has nothing trustworthy to read *and* a freshly
        generated brief could not be persisted either — most likely because
        `morning_briefs`/`brief_actions` do not exist in the connected
        database yet. Keeps the whole feature working exactly as it did
        before this phase until those tables are migrated.
        """
        return MorningBriefResponse(
            meta=demo_data.BRIEF_META,
            preparedFor=public_user_dict(self.user),
            executiveSummary=demo_data.EXECUTIVE_SUMMARY_TEXT,
            topPriorities=demo_data.PRIORITIES,
            criticalRisks=demo_data.RISKS,
            meetings=self._meetings(),
            clientsNeedingAttention=demo_data.CLIENTS_NEEDING_ATTENTION,
            importantEmails=self._important_emails(),
            suggestedFocus=demo_data.SUGGESTED_FOCUS,
            recommendedDelegation=demo_data.RECOMMENDED_DELEGATION,
            actionChecklist=demo_data.ACTION_CHECKLIST,
            closing=demo_data.CLOSING_ANSWER,
        )

    def _meetings(self) -> list[dict]:
        # Goes through `MeetingService` rather than `demo_data.MEETINGS`
        # directly, so the brief reflects real meetings the moment
        # `meetings` has rows, matching what `OverviewService` already does.
        return [
            {
                "id": meeting["id"],
                "time": meeting["startTime"],
                "title": meeting["title"],
                "attendees": [attendee["name"] for attendee in meeting["attendees"]],
                "prepStatus": meeting["prepStatus"],
                "note": meeting["prepReason"],
            }
            for meeting in MeetingService(self.db, self.user).list_meetings()
        ]

    def _important_emails(self) -> list[dict]:
        # Goes through `InboxService` rather than `demo_data.EMAILS`
        # directly, for the same reason as `_meetings()` above.
        emails = InboxService(self.db, self.user).list_emails()
        by_id = {email["id"]: email for email in emails}

        # Prefer the curated mock ordering when those stable ids are present
        # (fallback path). Database-backed emails use UUID primary keys, so
        # fall through to priority ranking rather than returning an empty
        # Important Emails section.
        selected = [by_id[email_id] for email_id in _BRIEF_EMAIL_IDS if email_id in by_id]
        if not selected:
            priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            selected = sorted(
                emails,
                key=lambda email: (priority_rank.get(email["priority"], 9), email["id"]),
            )[: len(_BRIEF_EMAIL_IDS)]

        return [
            {
                "id": email["id"],
                "sender": email["sender"]["name"],
                "subject": email["subject"],
                "summary": email["aiSummary"],
                "priority": email["priority"],
                "waitingSince": email["timeLabel"],
            }
            for email in selected
        ]
