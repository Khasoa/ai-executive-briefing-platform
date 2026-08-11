"""Weekly Intelligence & Next Week Outlook from user-scoped persisted data."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Email, Meeting, NotionItem, Opportunity, User, WeeklyDigest, WorkItem
from app.schemas.weekly_digest import (
    DataCoverageSchema,
    NextWeekOutlookSchema,
    WeeklyDigestResponse,
)
from app.services import demo_data
from app.services.demo_user import is_demo_user
from app.services.email_classification import is_executive_priority_email
from app.services.inbox_service import InboxService
from app.services.mapping_utils import relative_time_label, stringify_id
from app.services.meeting_windows import classify_meeting_at, relative_meeting_label
from app.services.time_windows import rolling_days_bounds, upcoming_bounds

logger = logging.getLogger("briefly.weekly_digest")

MIN_SIGNALS_FOR_AI = 3
# Past activity: rolling 7 local days. Outlook calendar: next 14 days.
OUTLOOK_MEETING_DAYS = 14
SCHEDULED_AHEAD_DAYS = 45
SECTION_KEYS = (
    "important_conversations",
    "decisions_and_approvals",
    "follow_ups",
    "unresolved_items",
    "notable_activity",
    "carry_into_next_week",
)
CRM_ATTENTION_RISKS = {"critical", "high"}


class WeeklyDigestService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_digest(self) -> WeeklyDigestResponse:
        week_start, week_end = self._current_week_bounds()
        existing = self._read_cached(week_start)
        if existing is not None and not self._cache_needs_refresh(existing):
            return self._to_response(existing)
        return self._generate_and_persist(week_start, week_end, force=False)

    def regenerate(self) -> WeeklyDigestResponse:
        week_start, week_end = self._current_week_bounds()
        return self._generate_and_persist(week_start, week_end, force=True)

    def _current_week_bounds(self) -> tuple[date, date]:
        start, end, _, _ = rolling_days_bounds(self.user, days=7)
        return start, end

    def _next_week_bounds(self) -> tuple[datetime, datetime]:
        return upcoming_bounds(self.user, days=OUTLOOK_MEETING_DAYS)

    def _cache_needs_refresh(self, row: WeeklyDigest) -> bool:
        """Refresh quiet/stale caches when live synced activity now exists."""
        quiet = (row.email_count or 0) == 0 and not (row.sources or [])
        headline = (row.headline or "").lower()
        if quiet or headline.startswith("quiet"):
            context = self._gather_context(row.week_start, row.week_end or self._current_week_bounds()[1])
            return self._signal_count(context) > 0
        return False

    def _read_cached(self, week_start: date) -> WeeklyDigest | None:
        try:
            return (
                self.db.query(WeeklyDigest)
                .filter(
                    WeeklyDigest.user_id == self.user.id,
                    WeeklyDigest.week_start == week_start,
                )
                .first()
            )
        except SQLAlchemyError:
            logger.warning("Could not read weekly_digests", exc_info=True)
            self.db.rollback()
            return None

    def _generate_and_persist(
        self, week_start: date, week_end: date, *, force: bool
    ) -> WeeklyDigestResponse:
        context = self._gather_context(week_start, week_end)
        content = self._build_content(context, week_start, week_end)

        try:
            row = self._read_cached(week_start)
            now = datetime.now(timezone.utc)
            if row is None:
                row = WeeklyDigest(
                    user_id=self.user.id,
                    week_start=week_start,
                    week_end=week_end,
                )
                self.db.add(row)

            row.week_end = week_end
            row.headline = content["headline"]
            row.summary = content["summary"]
            row.planning_note = content["planning_note"]
            row.confidence = content["confidence"]
            row.generated_by = content["generated_by"]
            row.sources = content["sources"]
            row.email_count = content["email_count"]
            row.sections = content["sections"]
            row.generated_at = now
            self.db.commit()
            self.db.refresh(row)
            return self._to_response(row)
        except SQLAlchemyError:
            logger.warning("Could not persist weekly digest — returning ephemeral", exc_info=True)
            self.db.rollback()
            return self._ephemeral_response(content, week_start, week_end)

    # -- cross-system context (user-scoped; never demo leakage) -------------

    def _gather_context(self, week_start: date, week_end: date) -> dict[str, Any]:
        _, _, start_dt, end_dt = rolling_days_bounds(self.user, days=7)
        # Honour caller week bounds when regenerating a specific cached week.
        from app.services.time_windows import user_zone

        zone = user_zone(self.user)
        start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=zone).astimezone(
            timezone.utc
        )
        end_dt = datetime.combine(week_end, datetime.max.time(), tzinfo=zone).astimezone(
            timezone.utc
        )
        next_start, next_end = self._next_week_bounds()
        ahead_end = next_start + timedelta(days=SCHEDULED_AHEAD_DAYS)

        emails = self._emails_in_window(week_start, week_end)
        meetings_past = self._dedupe_meetings(self._meetings_in_range(start_dt, end_dt))
        meetings_upcoming = self._dedupe_meetings(self._meetings_in_range(next_start, next_end))
        meetings_ahead = self._dedupe_meetings(
            [
                m
                for m in self._meetings_in_range(next_end, ahead_end)
                if m["id"] not in {x["id"] for x in meetings_upcoming}
            ]
        )
        opportunities = self._opportunities_attention()
        notion = self._notion_activity(start_dt, end_dt)
        work = self._work_activity()

        summaries = sum(1 for e in emails if (e.get("aiSummary") or "").strip())
        email_note = ""
        if emails and summaries == 0:
            email_note = (
                "Email view is limited to subject, sender, labels, and metadata — "
                "message bodies are not stored, so Briefly will not invent body summaries."
            )
        elif emails and summaries < len(emails):
            email_note = (
                f"{summaries} of {len(emails)} threads have AI summaries; "
                "others are described from subject/metadata only."
            )

        sources_with_data: list[str] = []
        if emails:
            sources_with_data.append("Gmail")
        if meetings_past or meetings_upcoming or meetings_ahead:
            sources_with_data.append("Google Calendar")
        if opportunities:
            sources_with_data.append("GoHighLevel")
        if notion:
            sources_with_data.append("Notion")
        for label in work.get("providers") or []:
            if label not in sources_with_data:
                sources_with_data.append(label)

        coverage = {
            "emailCount": len(emails),
            "emailSummariesAvailable": summaries > 0,
            "emailNote": email_note,
            "meetingCount": len(meetings_past) + len(meetings_upcoming) + len(meetings_ahead),
            "opportunityCount": len(opportunities),
            "workItemCount": int(work.get("openCount") or 0),
            "notionItemCount": len(notion),
            "sourcesWithData": sources_with_data,
            "emailActivitySummary": self._email_activity_summary(emails),
        }

        return {
            "emails": emails,
            "meetingsPast": meetings_past,
            "meetingsUpcoming": meetings_upcoming,
            "meetingsAhead": meetings_ahead,
            "opportunities": opportunities,
            "notionItems": notion,
            "workItems": work,
            "dataCoverage": coverage,
        }

    @staticmethod
    def _dedupe_meetings(meetings: list[dict]) -> list[dict]:
        """Collapse display duplicates that share title + start (distinct Google IDs)."""
        seen: set[tuple[str, str]] = set()
        out: list[dict] = []
        for meeting in meetings:
            key = (
                (meeting.get("title") or "").strip().lower(),
                (meeting.get("startsAt") or "")[:16],
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(meeting)
        return out

    @staticmethod
    def _email_activity_summary(emails: list[dict], *, limit: int = 5) -> dict[str, Any]:
        """Deterministic metadata aggregates — never invents body content."""
        from collections import Counter

        senders: Counter[str] = Counter()
        labels: Counter[str] = Counter()
        for email in emails:
            sender = email.get("sender") or {}
            name = (sender.get("name") or sender.get("email") or "Unknown").strip()
            senders[name] += 1
            for label in email.get("labels") or []:
                if label and str(label).upper() not in ("INBOX", "UNREAD", "CATEGORY_PERSONAL"):
                    labels[str(label)] += 1
        top_senders = [{"name": n, "count": c} for n, c in senders.most_common(limit)]
        top_labels = [{"label": n, "count": c} for n, c in labels.most_common(limit)]
        unread = sum(1 for e in emails if e.get("unread"))
        high_pri = sum(
            1
            for e in emails
            if e.get("priority") in ("critical", "high") or e.get("category") == "high-priority"
        )
        return {
            "total": len(emails),
            "unread": unread,
            "highPriorityOrStarred": high_pri,
            "topSenders": top_senders,
            "topLabels": top_labels,
        }

    def _emails_in_window(self, week_start: date, week_end: date) -> list[dict]:
        from app.services.time_windows import user_zone

        zone = user_zone(self.user)
        start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=zone).astimezone(
            timezone.utc
        )
        end_dt = datetime.combine(week_end, datetime.max.time(), tzinfo=zone).astimezone(
            timezone.utc
        )
        try:
            rows = (
                self.db.query(Email)
                .filter(
                    Email.user_id == self.user.id,
                    Email.received_at.isnot(None),
                    Email.received_at >= start_dt,
                    Email.received_at <= end_dt,
                )
                .order_by(Email.received_at.desc())
                .limit(80)
                .all()
            )
            if rows:
                return [InboxService(self.db, self.user)._to_dict(row) for row in rows]
        except SQLAlchemyError:
            logger.warning("Email query for weekly digest failed", exc_info=True)
            self.db.rollback()

        if is_demo_user(self.user):
            return list(demo_data.EMAILS)[:40]
        return []

    def _meetings_in_range(self, start: datetime, end: datetime) -> list[dict]:
        try:
            rows = (
                self.db.query(Meeting)
                .filter(
                    Meeting.user_id == self.user.id,
                    Meeting.starts_at >= start,
                    Meeting.starts_at <= end,
                )
                .order_by(Meeting.starts_at.asc())
                .limit(40)
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Meeting query for weekly digest failed", exc_info=True)
            self.db.rollback()
            return []

        out: list[dict] = []
        for row in rows:
            intel = row.intelligence or {}
            prep = ""
            if isinstance(intel, dict):
                prep = str(
                    intel.get("executiveSummary")
                    or intel.get("summary")
                    or row.prep_reason
                    or ""
                ).strip()
            out.append(
                {
                    "id": stringify_id(row.id),
                    "title": row.title,
                    "startsAt": row.starts_at.isoformat() if row.starts_at else "",
                    "endsAt": row.ends_at.isoformat() if row.ends_at else "",
                    "type": row.type,
                    "location": row.location,
                    "prepStatus": row.prep_status,
                    "prepNote": prep[:320],
                    "company": (row.company or {}).get("name") if isinstance(row.company, dict) else "",
                    "source": "Google Calendar",
                    "window": classify_meeting_at(row.starts_at, self.user),
                    "relativeLabel": relative_meeting_label(row.starts_at, self.user),
                }
            )
        return out

    def _opportunities_attention(self) -> list[dict]:
        """User-owned CRM rows only — never load_rows_with_fallback demo leakage."""
        try:
            rows = (
                self.db.query(Opportunity)
                .filter(Opportunity.user_id == self.user.id)
                .order_by(Opportunity.value.desc())
                .limit(40)
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Opportunity query for weekly digest failed", exc_info=True)
            self.db.rollback()
            return []

        out: list[dict] = []
        for row in rows:
            risk = (row.risk_level or "low").lower()
            needs = risk in CRM_ATTENTION_RISKS or bool((row.recommended_action or "").strip())
            if not needs and risk not in {"medium"}:
                continue
            if risk == "medium" and not (row.recommended_action or row.ai_summary):
                continue
            out.append(
                {
                    "id": stringify_id(row.id),
                    "company": row.company,
                    "stage": row.stage,
                    "value": row.value,
                    "probability": row.probability,
                    "riskLevel": risk,
                    "aiSummary": (row.ai_summary or "")[:320],
                    "recommendedAction": (row.recommended_action or "")[:320],
                    "closeDate": row.close_date.isoformat() if row.close_date else None,
                    "source": "GoHighLevel",
                }
            )
        return out[:15]

    def _notion_activity(self, start_dt: datetime, end_dt: datetime) -> list[dict]:
        try:
            rows = (
                self.db.query(NotionItem)
                .filter(
                    NotionItem.user_id == self.user.id,
                    NotionItem.archived.is_(False),
                    NotionItem.last_edited_at.isnot(None),
                    NotionItem.last_edited_at >= start_dt,
                    NotionItem.last_edited_at <= end_dt,
                )
                .order_by(NotionItem.last_edited_at.desc())
                .limit(30)
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Notion query for weekly digest failed", exc_info=True)
            self.db.rollback()
            return []

        return [
            {
                "id": stringify_id(row.id),
                "title": row.title or "(untitled)",
                "kind": row.kind,
                "status": row.status,
                "dueAt": row.due_at.isoformat() if row.due_at else None,
                "preview": (row.content_preview or "")[:240],
                "source": "Notion",
            }
            for row in rows
        ]

    def _work_activity(self) -> dict[str, Any]:
        empty = {
            "connected": False,
            "providers": [],
            "overdue": [],
            "dueSoon": [],
            "highPriority": [],
            "blocked": [],
            "completedThisWeek": [],
            "openCount": 0,
            "overdueCount": 0,
            "ownership": [],
        }
        try:
            from app.services.work_item_service import PROVIDER_LABELS, WorkItemService

            # Only include when the user actually has work_items rows (not merely connected).
            rows = (
                self.db.query(WorkItem.provider)
                .filter(WorkItem.user_id == self.user.id, WorkItem.archived.is_(False))
                .distinct()
                .all()
            )
            if not rows:
                return empty

            signals = WorkItemService(self.db).executive_summary_signals(self.user)
            # Prefer labels from persisted rows so connected-but-empty Integrations
            # are not required once real WorkItem data exists.
            from_rows = [
                PROVIDER_LABELS.get(provider, provider)
                for (provider,) in rows
                if provider
            ]
            signals["providers"] = from_rows or list(signals.get("providers") or [])
            signals["connected"] = True
            return signals
        except Exception:
            logger.warning("Work item context for weekly digest failed", exc_info=True)
            return empty

    # -- content generation -------------------------------------------------

    def _signal_count(self, context: dict[str, Any]) -> int:
        work = context.get("workItems") or {}
        return (
            len(context.get("emails") or [])
            + len(context.get("meetingsPast") or [])
            + len(context.get("meetingsUpcoming") or [])
            + len(context.get("meetingsAhead") or [])
            + len(context.get("opportunities") or [])
            + len(context.get("notionItems") or [])
            + len(work.get("overdue") or [])
            + len(work.get("dueSoon") or [])
            + len(work.get("completedThisWeek") or [])
        )

    def _build_content(
        self, context: dict[str, Any], week_start: date, week_end: date
    ) -> dict:
        week_label = self._week_label(week_start, week_end)
        email_count = len(context.get("emails") or [])
        coverage = context.get("dataCoverage") or {}
        signals = self._signal_count(context)

        if signals == 0:
            return self._empty_content(week_label, coverage)

        factual_outlook = self._factual_outlook(context)

        if signals < MIN_SIGNALS_FOR_AI:
            curated = self._curated_from_context(context, week_label, factual_outlook)
            curated["email_count"] = email_count
            curated["generated_by"] = "curated"
            return curated

        from app.services.ai_service import AIService

        ai_context = {
            "week": week_label,
            "weekStart": week_start.isoformat(),
            "weekEnd": week_end.isoformat(),
            "executive": {
                "name": self.user.full_name or self.user.name,
                "role": self.user.role,
                "company": self.user.company,
                "timezone": self.user.timezone or "UTC",
            },
            "dataCoverage": coverage,
            # Compact aggregates first — avoid shipping every email body to OpenAI.
            "emailActivitySummary": coverage.get("emailActivitySummary") or {},
            "emails": [
                {
                    "id": e["id"],
                    "subject": e["subject"],
                    "sender": e.get("sender"),
                    "priority": e.get("priority"),
                    "category": e.get("category"),
                    "aiSummary": (e.get("aiSummary") or "")[:240],
                    "unread": e.get("unread"),
                    "timeLabel": e.get("timeLabel"),
                    "labels": (e.get("labels") or [])[:6],
                    "hasBodySummary": bool((e.get("aiSummary") or "").strip()),
                }
                for e in (context.get("emails") or [])[:25]
            ],
            "meetingsPast": context.get("meetingsPast") or [],
            "meetingsUpcoming": context.get("meetingsUpcoming") or [],
            "meetingsAhead": context.get("meetingsAhead") or [],
            "opportunities": context.get("opportunities") or [],
            "notionItems": context.get("notionItems") or [],
            "workItems": context.get("workItems") or {},
            "factualOutlook": factual_outlook,
        }
        ai = AIService(self.db, self.user).generate_weekly_digest(ai_context)
        if ai is None:
            curated = self._curated_from_context(context, week_label, factual_outlook)
            curated["email_count"] = email_count
            curated["generated_by"] = "curated"
            return curated

        outlook = ai.get("next_week_outlook") or {}
        # Prefer factual lists when AI omitted them; keep AI recommendations.
        merged_outlook = self._merge_outlook(factual_outlook, outlook)

        sources = list(ai.get("sources") or [])
        for src in coverage.get("sourcesWithData") or []:
            if src not in sources:
                sources.append(src)

        return {
            "headline": ai["headline"],
            "summary": ai.get("week_summary") or ai["summary"],
            "planning_note": ai["planning_note"],
            "confidence": ai["confidence"],
            "generated_by": "openai",
            "sources": sources,
            "email_count": email_count,
            "sections": {
                "important_conversations": ai["important_conversations"],
                "decisions_and_approvals": ai["decisions_and_approvals"],
                "follow_ups": ai["follow_ups"],
                "unresolved_items": ai["unresolved_items"],
                "notable_activity": ai["notable_activity"],
                "carry_into_next_week": ai["carry_into_next_week"],
                "next_week_outlook": merged_outlook,
                "data_coverage": coverage,
            },
        }

    def _merge_outlook(self, factual: dict, ai_outlook: dict) -> dict:
        def pick(key: str, *, prefer_ai: bool = False) -> list:
            ai_items = ai_outlook.get(key) or []
            fact_items = factual.get(key) or []
            if prefer_ai and ai_items:
                return ai_items
            return fact_items or ai_items

        return {
            "upcoming_meetings": pick("upcoming_meetings"),
            "upcoming_deadlines": pick("upcoming_deadlines"),
            "overdue_work": pick("overdue_work"),
            "crm_attention": pick("crm_attention"),
            "email_follow_ups": pick("email_follow_ups"),
            "work_items": pick("work_items"),
            "carry_forward": pick("carry_forward") or pick("email_follow_ups"),
            "recommended_priorities": pick("recommended_priorities", prefer_ai=True),
            "risks_and_watchouts": pick("risks_and_watchouts", prefer_ai=True),
            "workload_signals": pick("workload_signals")
            or pick("workload_signals", prefer_ai=True),
        }

    def _factual_outlook(self, context: dict[str, Any]) -> dict[str, list[dict]]:
        emails = context.get("emails") or []
        work = context.get("workItems") or {}

        def item(
            prefix: str,
            index: int,
            title: str,
            detail: str,
            source: str,
            *,
            email_ids: list[str] | None = None,
            kind: str = "fact",
        ) -> dict:
            return {
                "id": f"{prefix}_{index}",
                "title": title,
                "detail": (detail or "")[:360],
                "source": source,
                "emailIds": email_ids or [],
                "kind": kind,
            }

        upcoming_meetings = [
            item(
                "um",
                i,
                m["title"],
                (
                    f"{m.get('relativeLabel') or m.get('startsAt', '')[:16].replace('T', ' ')}"
                    + (f" · {m['company']}" if m.get("company") else "")
                    + (
                        " · this week"
                        if m.get("window") in ("today", "tomorrow", "this_week")
                        else ""
                    )
                    + (f" — {m['prepNote']}" if m.get("prepNote") else "")
                ),
                "Google Calendar",
            )
            for i, m in enumerate((context.get("meetingsUpcoming") or [])[:8])
        ]
        # Further-ahead scheduled events: planning context, not prepare-today urgency.
        for i, m in enumerate((context.get("meetingsAhead") or [])[:4]):
            title_l = (m.get("title") or "").lower()
            recurring_hint = "monthly" in title_l or "recurring" in title_l
            upcoming_meetings.append(
                item(
                    "ua",
                    i,
                    m["title"],
                    (
                        "Planning context"
                        + (" · recurring" if recurring_hint else "")
                        + f" · {m.get('relativeLabel') or m.get('startsAt', '')[:16].replace('T', ' ')}"
                        + (f" · {m['company']}" if m.get("company") else "")
                        + " — not a today preparation item"
                    ),
                    "Google Calendar",
                )
            )

        upcoming_deadlines = [
            item(
                "ud",
                i,
                w.get("title") or "Deadline",
                f"Due {w.get('dueAt') or 'soon'}"
                + (f" · {w.get('assignee') or w.get('assigneeName') or ''}".rstrip(" ·")),
                w.get("source") or "monday.com",
            )
            for i, w in enumerate((work.get("dueSoon") or [])[:8])
        ]

        overdue_work = [
            item(
                "ow",
                i,
                w.get("title") or "Overdue",
                f"Overdue · {w.get('status') or 'open'}"
                + (f" · {w.get('assignee') or w.get('assigneeName') or ''}".rstrip(" ·")),
                w.get("source") or "monday.com",
            )
            for i, w in enumerate((work.get("overdue") or [])[:8])
        ]

        crm_attention = [
            item(
                "crm",
                i,
                f"{o['company']} · {o['stage']}",
                o.get("recommendedAction")
                or o.get("aiSummary")
                or f"Risk {o.get('riskLevel')} · probability {o.get('probability')}%",
                "GoHighLevel",
            )
            for i, o in enumerate((context.get("opportunities") or [])[:8])
        ]

        needs_reply = [e for e in emails if is_executive_priority_email(e)]
        email_follow_ups = []
        for i, e in enumerate(needs_reply[:6]):
            sender = e.get("sender") or {}
            name = sender.get("name") or sender.get("email") or "Unknown"
            detail = (e.get("aiSummary") or "").strip()
            if not detail:
                detail = f"From {name} — subject/metadata only; no stored body summary."
            email_follow_ups.append(
                item("ef", i, e.get("subject") or "(no subject)", detail, "Gmail", email_ids=[e["id"]])
            )

        work_items = [
            item(
                "wi",
                i,
                w.get("title") or "Work item",
                f"{w.get('priority') or 'priority'} · {w.get('status') or 'open'}",
                w.get("source") or "monday.com",
            )
            for i, w in enumerate((work.get("highPriority") or [])[:6])
        ]

        carry_forward = email_follow_ups[:3] or overdue_work[:2] or crm_attention[:2]

        workload_signals: list[dict] = []
        meeting_n = len(context.get("meetingsUpcoming") or [])
        if meeting_n >= 5:
            workload_signals.append(
                item(
                    "wl",
                    0,
                    f"{meeting_n} meetings in the next 7 days",
                    "Calendar density is high — protect focus blocks.",
                    "Google Calendar",
                )
            )
        if int(work.get("overdueCount") or 0) >= 3:
            workload_signals.append(
                item(
                    "wl",
                    1,
                    f"{work['overdueCount']} overdue work items",
                    "Clear blockers before adding new commitments.",
                    (work.get("providers") or ["monday.com"])[0],
                )
            )
        for i, own in enumerate((work.get("ownership") or [])[:3]):
            workload_signals.append(
                item(
                    "wl",
                    10 + i,
                    f"{own.get('assignee')}: {own.get('attentionItems')} attention items",
                    "Ownership concentration may create delivery risk.",
                    (work.get("providers") or ["monday.com"])[0],
                )
            )

        # Light recommendations from facts — explicitly marked.
        recommended: list[dict] = []
        idx = 0
        for src_list, label in (
            (overdue_work[:2], "Resolve overdue work"),
            (crm_attention[:2], "Address CRM risk"),
            (email_follow_ups[:2], "Clear email follow-ups"),
            (upcoming_meetings[:1], "Prep key meetings"),
        ):
            for entry in src_list:
                recommended.append(
                    {
                        **entry,
                        "id": f"rp_{idx}",
                        "title": f"{label}: {entry['title']}",
                        "kind": "recommendation",
                    }
                )
                idx += 1
                if idx >= 5:
                    break
            if idx >= 5:
                break

        risks = []
        for i, entry in enumerate((work.get("blocked") or [])[:4]):
            risks.append(
                item(
                    "rk",
                    i,
                    entry.get("title") or "Blocked work",
                    "Blocked / stalled — may slip next week.",
                    entry.get("source") or "monday.com",
                    kind="fact",
                )
            )

        return {
            "upcoming_meetings": upcoming_meetings,
            "upcoming_deadlines": upcoming_deadlines,
            "overdue_work": overdue_work,
            "crm_attention": crm_attention,
            "email_follow_ups": email_follow_ups,
            "work_items": work_items,
            "carry_forward": carry_forward,
            "recommended_priorities": recommended,
            "risks_and_watchouts": risks,
            "workload_signals": workload_signals,
        }

    def _empty_content(self, week_label: str, coverage: dict) -> dict:
        if is_demo_user(self.user):
            curated = dict(demo_data.WEEKLY_DIGEST)
            sections = {
                "important_conversations": curated.get("importantConversations", []),
                "decisions_and_approvals": curated.get("decisionsAndApprovals", []),
                "follow_ups": curated.get("followUps", []),
                "unresolved_items": curated.get("unresolvedItems", []),
                "notable_activity": curated.get("notableActivity", []),
                "carry_into_next_week": curated.get("carryIntoNextWeek", []),
                "next_week_outlook": curated.get("nextWeekOutlook")
                or {
                    "upcoming_meetings": [],
                    "upcoming_deadlines": [],
                    "overdue_work": [],
                    "crm_attention": [],
                    "email_follow_ups": [],
                    "work_items": [],
                    "carry_forward": curated.get("carryIntoNextWeek", []),
                    "recommended_priorities": [],
                    "risks_and_watchouts": [],
                    "workload_signals": [],
                },
                "data_coverage": {
                    **coverage,
                    "emailCount": len(demo_data.EMAILS),
                    "sourcesWithData": ["Gmail"],
                    "emailNote": "",
                },
            }
            return {
                "headline": curated["headline"],
                "summary": curated["summary"],
                "planning_note": curated.get("planningNote", ""),
                "confidence": curated.get("confidence", "medium"),
                "generated_by": "curated",
                "sources": curated.get("sources", ["Gmail"]),
                "email_count": len(demo_data.EMAILS),
                "sections": sections,
            }

        return {
            "headline": f"Quiet week · {week_label}",
            "summary": (
                "No synced activity was found across email, calendar, CRM, Notion, "
                "or work tools for the last 7 days. Connect and sync integrations — "
                "Briefly only builds intelligence from your persisted data."
            ),
            "planning_note": (
                "When records land, regenerate for a cross-system outlook. "
                "A connected integration with zero synced rows stays empty by design."
            ),
            "confidence": "low",
            "generated_by": "curated",
            "sources": [],
            "email_count": 0,
            "sections": {
                **{key: [] for key in SECTION_KEYS},
                "next_week_outlook": {
                    "upcoming_meetings": [],
                    "upcoming_deadlines": [],
                    "overdue_work": [],
                    "crm_attention": [],
                    "email_follow_ups": [],
                    "work_items": [],
                    "carry_forward": [],
                    "recommended_priorities": [],
                    "risks_and_watchouts": [],
                    "workload_signals": [],
                },
                "data_coverage": coverage,
            },
        }

    def _curated_from_context(
        self,
        context: dict[str, Any],
        week_label: str,
        outlook: dict[str, list[dict]],
    ) -> dict:
        emails = context.get("emails") or []
        coverage = context.get("dataCoverage") or {}

        if is_demo_user(self.user) and len(emails) >= MIN_SIGNALS_FOR_AI:
            return self._empty_content(week_label, coverage)

        high = [e for e in emails if e.get("priority") in ("critical", "high") and is_executive_priority_email(e)]
        needs_reply = [e for e in emails if is_executive_priority_email(e)]
        waiting = [e for e in emails if e.get("category") == "waiting"]

        def to_email_item(email: dict, prefix: str, index: int) -> dict:
            sender = email.get("sender") or {}
            name = sender.get("name") or sender.get("email") or "Unknown"
            summary = (email.get("aiSummary") or "").strip()
            if not summary:
                summary = (
                    f"From {name}. Limited email view — subject/metadata only; "
                    "no body summary is stored."
                )
            return {
                "id": f"{prefix}_{index}",
                "title": email.get("subject") or "(no subject)",
                "detail": summary[:320],
                "source": "Gmail",
                "emailIds": [email["id"]],
                "kind": "fact",
            }

        important = [to_email_item(e, "imp", i) for i, e in enumerate(high[:5])]
        if not important:
            important = [to_email_item(e, "imp", i) for i, e in enumerate(emails[:3])]

        # Meetings past week as notable (+ scheduled ahead when useful)
        notable = [
            {
                "id": f"mp_{i}",
                "title": m["title"],
                "detail": m.get("prepNote")
                or f"Meeting · {m.get('startsAt', '')[:16].replace('T', ' ')}",
                "source": "Google Calendar",
                "emailIds": [],
                "kind": "fact",
            }
            for i, m in enumerate((context.get("meetingsPast") or [])[:4])
        ]
        for i, m in enumerate((context.get("meetingsAhead") or [])[:3]):
            notable.append(
                {
                    "id": f"ma_{i}",
                    "title": m["title"],
                    "detail": f"Coming up · {m.get('startsAt', '')[:16].replace('T', ' ')}",
                    "source": "Google Calendar",
                    "emailIds": [],
                    "kind": "fact",
                }
            )
        for i, n in enumerate((context.get("notionItems") or [])[:3]):
            notable.append(
                {
                    "id": f"no_{i}",
                    "title": n["title"],
                    "detail": n.get("preview") or f"Notion {n.get('kind')}",
                    "source": "Notion",
                    "emailIds": [],
                    "kind": "fact",
                }
            )
        for i, o in enumerate((context.get("opportunities") or [])[:2]):
            notable.append(
                {
                    "id": f"op_{i}",
                    "title": f"{o['company']} pipeline activity",
                    "detail": o.get("aiSummary") or f"{o['stage']} · risk {o['riskLevel']}",
                    "source": "GoHighLevel",
                    "emailIds": [],
                    "kind": "fact",
                }
            )

        work = context.get("workItems") or {}
        for i, w in enumerate((work.get("completedThisWeek") or [])[:3]):
            notable.append(
                {
                    "id": f"wc_{i}",
                    "title": f"Completed: {w.get('title')}",
                    "detail": w.get("status") or "Done this week",
                    "source": w.get("source") or "monday.com",
                    "emailIds": [],
                    "kind": "fact",
                }
            )

        follow_ups = [to_email_item(e, "fu", i) for i, e in enumerate(needs_reply[:5])]
        unresolved = [to_email_item(e, "un", i) for i, e in enumerate(waiting[:5])]
        if not unresolved:
            unresolved = [
                to_email_item(e, "un", i)
                for i, e in enumerate([e for e in needs_reply if e.get("unread")][:4])
            ]

        carry = outlook.get("carry_forward") or follow_ups[:3] or important[:2]
        sources = list(coverage.get("sourcesWithData") or [])
        if not sources and emails:
            sources = ["Gmail"]

        parts = []
        activity = coverage.get("emailActivitySummary") or {}
        if emails:
            total = activity.get("total") or len(emails)
            parts.append(f"{total} synced messages in the last 7 days")
            top = activity.get("topSenders") or []
            if top:
                names = ", ".join(f"{s['name']} ({s['count']})" for s in top[:3])
                parts.append(f"recent volume concentrated around {names}")
            if activity.get("unread"):
                parts.append(f"{activity['unread']} still unread")
        if context.get("meetingsPast"):
            parts.append(f"{len(context['meetingsPast'])} meetings on the calendar this week")
        if context.get("meetingsUpcoming") or context.get("meetingsAhead"):
            n = len(context.get("meetingsUpcoming") or []) + len(context.get("meetingsAhead") or [])
            parts.append(f"{n} upcoming meetings on the horizon")
        if context.get("opportunities"):
            parts.append(f"{len(context['opportunities'])} CRM items needing attention")
        if work.get("overdueCount"):
            parts.append(f"{work['overdueCount']} overdue work items")

        urgent = [e for e in emails if is_executive_priority_email(e)]
        if emails and not urgent and not (context.get("meetingsPast") or context.get("opportunities")):
            summary = (
                f"No urgent issues stand out for {week_label}, but there is real activity: "
                + "; ".join(parts)
                + "."
            )
        elif parts:
            summary = f"Cross-system view for {week_label}: " + "; ".join(parts) + "."
        else:
            summary = f"Limited activity in {week_label}."
        if coverage.get("emailNote"):
            summary = f"{summary} {coverage['emailNote']}"

        return {
            "headline": (
                f"Weekly intelligence · {week_label}"
                if emails or context.get("meetingsPast") or context.get("meetingsUpcoming")
                else f"Quiet week · {week_label}"
            ),
            "summary": summary,
            "planning_note": (
                "Facts below come from synced records. Recommended priorities are heuristic "
                "suggestions — regenerate when OpenAI is available for deeper synthesis."
            ),
            "confidence": "medium" if self._signal_count(context) >= MIN_SIGNALS_FOR_AI else "low",
            "generated_by": "curated",
            "sources": sources,
            "email_count": len(emails),
            "sections": {
                "important_conversations": important,
                "decisions_and_approvals": [],
                "follow_ups": follow_ups,
                "unresolved_items": unresolved,
                "notable_activity": notable,
                "carry_into_next_week": carry,
                "next_week_outlook": outlook,
                "data_coverage": coverage,
            },
        }

    # -- response mapping ---------------------------------------------------

    def _outlook_to_schema(self, raw: dict | None) -> NextWeekOutlookSchema:
        raw = raw or {}

        def items(snake: str, camel: str | None = None) -> list:
            camel = camel or snake
            data = raw.get(snake) or raw.get(camel) or []
            out = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                out.append(
                    {
                        "id": str(entry.get("id") or uuid4().hex[:8]),
                        "title": str(entry.get("title") or ""),
                        "detail": str(entry.get("detail") or ""),
                        "source": entry.get("source") or "Gmail",
                        "emailIds": [str(x) for x in (entry.get("emailIds") or []) if x],
                        "kind": entry.get("kind") if entry.get("kind") in ("fact", "recommendation") else "fact",
                    }
                )
            return out

        return NextWeekOutlookSchema(
            upcomingMeetings=items("upcoming_meetings", "upcomingMeetings"),
            upcomingDeadlines=items("upcoming_deadlines", "upcomingDeadlines"),
            overdueWork=items("overdue_work", "overdueWork"),
            crmAttention=items("crm_attention", "crmAttention"),
            emailFollowUps=items("email_follow_ups", "emailFollowUps"),
            workItems=items("work_items", "workItems"),
            carryForward=items("carry_forward", "carryForward"),
            recommendedPriorities=items("recommended_priorities", "recommendedPriorities"),
            risksAndWatchouts=items("risks_and_watchouts", "risksAndWatchouts"),
            workloadSignals=items("workload_signals", "workloadSignals"),
        )

    def _coverage_to_schema(self, raw: dict | None, email_count: int) -> DataCoverageSchema:
        raw = raw or {}
        return DataCoverageSchema(
            emailCount=int(raw.get("emailCount", email_count) or 0),
            emailSummariesAvailable=bool(raw.get("emailSummariesAvailable")),
            emailNote=str(raw.get("emailNote") or ""),
            meetingCount=int(raw.get("meetingCount") or 0),
            opportunityCount=int(raw.get("opportunityCount") or 0),
            workItemCount=int(raw.get("workItemCount") or 0),
            notionItemCount=int(raw.get("notionItemCount") or 0),
            sourcesWithData=list(raw.get("sourcesWithData") or []),
        )

    def _to_response(self, row: WeeklyDigest) -> WeeklyDigestResponse:
        sections = row.sections or {}
        summary = row.summary or ""
        return WeeklyDigestResponse(
            id=stringify_id(row.id),
            weekStart=row.week_start.isoformat(),
            weekEnd=row.week_end.isoformat(),
            weekLabel=self._week_label(row.week_start, row.week_end),
            headline=row.headline,
            summary=summary,
            weekSummary=summary,
            importantConversations=sections.get("important_conversations") or [],
            decisionsAndApprovals=sections.get("decisions_and_approvals") or [],
            followUps=sections.get("follow_ups") or [],
            unresolvedItems=sections.get("unresolved_items") or [],
            notableActivity=sections.get("notable_activity") or [],
            carryIntoNextWeek=sections.get("carry_into_next_week") or [],
            nextWeekOutlook=self._outlook_to_schema(sections.get("next_week_outlook")),
            planningNote=row.planning_note or "",
            confidence=row.confidence,  # type: ignore[arg-type]
            generatedBy=row.generated_by,  # type: ignore[arg-type]
            sources=list(row.sources or []),  # type: ignore[arg-type]
            emailCount=row.email_count,
            dataCoverage=self._coverage_to_schema(sections.get("data_coverage"), row.email_count),
            generatedAt=row.generated_at.isoformat() if row.generated_at else "",
            generatedLabel=relative_time_label(row.generated_at) if row.generated_at else "",
        )

    def _ephemeral_response(
        self, content: dict, week_start: date, week_end: date
    ) -> WeeklyDigestResponse:
        sections = content.get("sections") or {}
        now = datetime.now(timezone.utc)
        summary = content["summary"]
        return WeeklyDigestResponse(
            id=f"wd_{uuid4().hex[:10]}",
            weekStart=week_start.isoformat(),
            weekEnd=week_end.isoformat(),
            weekLabel=self._week_label(week_start, week_end),
            headline=content["headline"],
            summary=summary,
            weekSummary=summary,
            importantConversations=sections.get("important_conversations") or [],
            decisionsAndApprovals=sections.get("decisions_and_approvals") or [],
            followUps=sections.get("follow_ups") or [],
            unresolvedItems=sections.get("unresolved_items") or [],
            notableActivity=sections.get("notable_activity") or [],
            carryIntoNextWeek=sections.get("carry_into_next_week") or [],
            nextWeekOutlook=self._outlook_to_schema(sections.get("next_week_outlook")),
            planningNote=content.get("planning_note") or "",
            confidence=content.get("confidence") or "medium",
            generatedBy=content.get("generated_by") or "curated",
            sources=content.get("sources") or [],
            emailCount=content.get("email_count") or 0,
            dataCoverage=self._coverage_to_schema(
                sections.get("data_coverage"), content.get("email_count") or 0
            ),
            generatedAt=now.isoformat(),
            generatedLabel="just now",
        )

    @staticmethod
    def _week_label(week_start: date, week_end: date) -> str:
        if week_start.year == week_end.year and week_start.month == week_end.month:
            return f"{week_start.strftime('%b')} {week_start.day} – {week_end.day}, {week_end.year}"
        if week_start.year == week_end.year:
            return (
                f"{week_start.strftime('%b')} {week_start.day} – "
                f"{week_end.strftime('%b')} {week_end.day}, {week_end.year}"
            )
        return (
            f"{week_start.strftime('%b')} {week_start.day}, {week_start.year} – "
            f"{week_end.strftime('%b')} {week_end.day}, {week_end.year}"
        )
