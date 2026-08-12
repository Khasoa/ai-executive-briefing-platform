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
from app.services.demo_user import is_demo_user, public_user_dict
from app.services.email_classification import is_executive_priority_email
from app.services.inbox_service import InboxService
from app.services.mapping_utils import jsonb_or_default, relative_time_label, stringify_id
from app.services.meeting_intelligence import MeetingIntelligenceService
from app.services.meeting_service import MeetingService
from app.services.time_windows import local_today, overnight_bounds

logger = logging.getLogger("briefly.morning_brief")

# Emails promoted into the brief, in the order an executive should read them.
_BRIEF_EMAIL_IDS = ("em_1", "em_2", "em_3", "em_5", "em_4", "em_6")
_QUIET_MARKERS = (
    "no meetings, emails",
    "no meetings or emails",
    "requiring your attention",
    "nothing requiring",
    "no urgent",
)


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

        Re-runs AI (or curated failover) and overwrites today's report row.
        Existing `BriefAction` rows for today are never recreated here, so
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
            if self._should_refresh_quiet_brief(brief):
                return self._generate_and_persist()
            try:
                actions = self.db.query(BriefAction).filter(BriefAction.brief_id == brief.id).all()
            except SQLAlchemyError:
                actions = []
            return brief, actions

        return self._generate_and_persist()

    def _should_refresh_quiet_brief(self, brief: MorningBrief) -> bool:
        """Replace stale 'nothing to do' briefs when synced activity exists."""
        if is_demo_user(self.user):
            return False
        text = f"{brief.executive_summary or ''} {brief.headline or ''}".lower()
        looks_quiet = any(marker in text for marker in _QUIET_MARKERS) or (
            not (brief.sections or {}).get("priorities")
            and not (brief.sections or {}).get("risks")
            and "no " in text
        )
        if not looks_quiet:
            return False
        meetings = MeetingService(self.db, self.user).list_meetings()
        emails = InboxService(self.db, self.user).list_emails()
        return bool(meetings or emails)

    def _read_todays_brief(self) -> MorningBrief | None:
        today = local_today(self.user)
        return (
            self.db.query(MorningBrief)
            .filter(
                MorningBrief.user_id == self.user.id,
                MorningBrief.brief_date == today,
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
        today = local_today(self.user)

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

    def _generated_content(self) -> dict:
        """AI generation with curated / situational failover.

        Today's persisted `MorningBrief` row is the cache — `_load_or_generate_brief`
        skips this path when a row already exists. `regenerate()` always calls
        here so OpenAI is re-invoked only on explicit refresh.
        """
        from app.services.ai_service import AIService

        ai_content = AIService(self.db, self.user).generate_morning_brief_content()
        if ai_content is not None:
            return ai_content
        if is_demo_user(self.user):
            return self._curated_content()
        return self._situational_content_from_data()

    @staticmethod
    def _curated_content() -> dict:
        """Demo curated generator — identical behaviour when OpenAI is unavailable."""
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

    def _situational_content_from_data(self) -> dict:
        """Deterministic brief for real users when OpenAI is unavailable.

        Distinguishes: meetings today, prep needed today, this-week upcoming,
        meaningful non-urgent activity — never equates "no urgent" with "nothing".
        """
        intel = MeetingIntelligenceService(self.db, self.user)
        classified = intel.load_classified_meetings(include_past=False)
        today_meetings = [m for m in classified if m.get("window") == "today"]
        prep_today = [m for m in today_meetings if m.get("prepRecommended")]
        this_week = [
            m for m in classified if m.get("window") in ("tomorrow", "this_week")
        ]
        later_planning = [
            m for m in classified if m.get("window") in ("this_month", "later")
        ]

        emails = InboxService(self.db, self.user).list_emails()
        overnight_start, overnight_end = overnight_bounds(self.user)
        overnight_count = 0
        try:
            from app.models import Email as EmailModel

            overnight_count = (
                self.db.query(EmailModel)
                .filter(
                    EmailModel.user_id == self.user.id,
                    EmailModel.received_at.isnot(None),
                    EmailModel.received_at >= overnight_start,
                    EmailModel.received_at <= overnight_end,
                )
                .count()
            )
        except SQLAlchemyError:
            self.db.rollback()

        recent_emails = list(emails)
        unread = [e for e in recent_emails if e.get("unread")]
        meaningful = [e for e in recent_emails if is_executive_priority_email(e)]
        sources: list[str] = []
        if recent_emails:
            sources.append("Gmail")
        if classified:
            sources.append("Google Calendar")

        parts: list[str] = []
        if overnight_count:
            parts.append(f"{overnight_count} emails arrived overnight")
        elif recent_emails:
            parts.append(f"{len(recent_emails)} synced emails are available")
        if today_meetings:
            titles = ", ".join((m.get("title") or "Meeting") for m in today_meetings[:2])
            parts.append(f"{len(today_meetings)} meeting(s) today ({titles})")
            if prep_today:
                parts.append(f"{len(prep_today)} need preparation today")
            else:
                parts.append("none of today's meetings currently recommend prep")
        elif this_week:
            nxt = this_week[0]
            parts.append(
                f"no meetings today; next up this week is "
                f"{nxt.get('title')} ({nxt.get('relativeLabel') or 'soon'})"
            )
        elif later_planning:
            nxt = later_planning[0]
            parts.append(
                f"no meetings today or this week; "
                f"{nxt.get('title')} is on the later calendar "
                f"({nxt.get('relativeLabel') or 'planning'}) — not a today prep item"
            )
        if meaningful and not any(
            e.get("priority") in ("critical", "high") for e in meaningful
        ):
            parts.append(f"{len(meaningful)} threads look worth a glance (unread or starred)")

        has_activity = bool(recent_emails or classified)
        has_urgent = bool(meaningful or prep_today or today_meetings)

        if not has_activity:
            summary = (
                "No synced email or calendar activity is available yet. "
                "Connect Gmail and Google Calendar, then sync — Briefly only briefs from your data."
            )
            headline = "Waiting on synced activity"
            confidence = "low"
        elif not has_urgent:
            summary = (
                "No meetings require preparation today and nothing is flagged urgent. "
                + ("Still, " + "; ".join(parts) + "." if parts else "")
            )
            if recent_emails and not any(
                (e.get("aiSummary") or "").strip() for e in recent_emails[:5]
            ):
                summary += (
                    " Email view is limited to subject/metadata — bodies are not stored."
                )
            headline = "Quiet on urgencies · activity still moving"
            confidence = "medium"
        else:
            summary = "Here's what stands out from your synced systems: " + "; ".join(parts) + "."
            headline = "Morning situational brief"
            confidence = "medium"

        priorities = []
        rank = 1
        for meeting in prep_today[:3] or today_meetings[:3]:
            priorities.append(
                {
                    "id": f"pri_meet_{rank}",
                    "rank": rank,
                    "title": meeting.get("title") or "Meeting today",
                    "detail": meeting.get("prepReason")
                    or meeting.get("relativeLabel")
                    or "On today's calendar",
                    "urgency": "high" if meeting.get("prepRecommended") else "medium",
                    "owner": self.user.name or "You",
                    "source": "Google Calendar",
                }
            )
            rank += 1
        for email in meaningful[:4]:
            urg = (
                email.get("priority")
                if email.get("priority") in ("critical", "high", "medium", "low")
                else "medium"
            )
            priorities.append(
                {
                    "id": f"pri_mail_{rank}",
                    "rank": rank,
                    "title": email.get("subject") or "(no subject)",
                    "detail": (email.get("aiSummary") or "").strip()
                    or f"From {(email.get('sender') or {}).get('name') or 'Unknown'} — subject/metadata only.",
                    "urgency": urg,
                    "owner": self.user.name or "You",
                    "source": "Gmail",
                }
            )
            rank += 1

        focus = {
            "headline": "Today's meetings & mail" if priorities else "Monitor the inbox",
            "rationale": summary.strip()[:280],
            "blocks": [
                {
                    "id": f"blk_{i}",
                    "start": "09:00",
                    "end": "09:30",
                    "label": p["title"][:80],
                    "reason": p["detail"][:160],
                    "kind": "review",
                }
                for i, p in enumerate(priorities[:3])
            ]
            or (
                [
                    {
                        "id": "blk_0",
                        "start": "09:00",
                        "end": "09:20",
                        "label": "Scan overnight email",
                        "reason": f"{overnight_count} messages in the overnight window",
                        "kind": "review",
                    }
                ]
                if overnight_count
                else []
            ),
        }
        return {
            "headline": headline,
            "executive_summary": summary.strip(),
            "confidence": confidence,
            "sources": sources or ["Gmail"],
            "sections": {
                "priorities": priorities,
                "risks": [],
                "clients": [],
                "focus": focus,
                "delegation": [],
            },
            "closing": {
                "question": "What should I clear first?",
                "answer": (
                    "Start with today's meetings that need prep, then skim unread or starred threads. "
                    "Later calendar items are planning context, not today urgency."
                    if priorities or overnight_count
                    else "Sync more systems or regenerate after new mail arrives."
                ),
                "bullets": [p["title"][:120] for p in priorities[:3]]
                or (
                    [f"Review {overnight_count} overnight emails"]
                    if overnight_count
                    else ["Check Integrations if this stays empty"]
                ),
            },
            "checklist": [
                {
                    "label": p["title"][:120],
                    "category": "Review",
                    "due": "Today",
                    "done": False,
                }
                for p in priorities[:5]
            ]
            or [
                {
                    "label": "Scan overnight inbox for anything that needs a reply",
                    "category": "Reply",
                    "due": "Today",
                    "done": False,
                }
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
        """Brief meeting strip: today first, then this week — not distant prep noise."""
        intel = MeetingIntelligenceService(self.db, self.user)
        classified = intel.load_classified_meetings(include_past=False)
        selected = [
            m
            for m in classified
            if m.get("window") in ("today", "tomorrow", "this_week")
        ][:8]
        if not selected and is_demo_user(self.user):
            return [
                {
                    "id": meeting["id"],
                    "time": meeting["startTime"],
                    "title": meeting["title"],
                    "attendees": [attendee["name"] for attendee in meeting["attendees"]],
                    "prepStatus": meeting["prepStatus"],
                    "note": meeting["prepReason"],
                }
                for meeting in MeetingService(self.db, self.user).list_meetings()[:8]
            ]

        return [
            {
                "id": meeting["id"],
                "time": meeting.get("startTime") or "",
                "title": meeting.get("title") or "Meeting",
                "attendees": [
                    a.get("name") or a.get("email") or ""
                    for a in (meeting.get("attendees") or [])
                    if isinstance(a, dict)
                ],
                "prepStatus": (
                    "needs-prep"
                    if meeting.get("prepRecommended")
                    else meeting.get("prepStatus") or "ready"
                ),
                "note": (
                    meeting.get("prepReason")
                    or (
                        f"Today · {meeting.get('relativeLabel')}"
                        if meeting.get("window") == "today"
                        else f"{meeting.get('window', 'upcoming').replace('_', ' ')} · "
                        f"{meeting.get('relativeLabel') or ''}"
                    )
                ).strip(),
            }
            for meeting in selected
        ]

    def _important_emails(self) -> list[dict]:
        emails = InboxService(self.db, self.user).list_emails()
        by_id = {email["id"]: email for email in emails}

        selected = [by_id[email_id] for email_id in _BRIEF_EMAIL_IDS if email_id in by_id]
        if not selected:
            priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}

            def rank(email: dict) -> tuple:
                urgent = 0 if is_executive_priority_email(email) else 1
                # Keep promo/newsletter out of the top of importantEmails.
                noise = 2 if (email.get("category") or "") in (
                    "promotional",
                    "newsletter",
                    "automated",
                ) else 0
                return (
                    urgent + noise,
                    priority_rank.get(email.get("priority"), 9),
                    email.get("id") or "",
                )

            selected = [
                e
                for e in sorted(emails, key=rank)
                if (e.get("category") or "") not in ("promotional", "newsletter", "automated")
            ][:6] or sorted(emails, key=rank)[:6]

        return [
            {
                "id": email["id"],
                "sender": email["sender"]["name"],
                "subject": email["subject"],
                "summary": email["aiSummary"]
                or f"Subject/metadata only — from {email['sender'].get('email') or email['sender'].get('name')}.",
                "priority": email["priority"],
                "waitingSince": email["timeLabel"],
            }
            for email in selected
        ]
