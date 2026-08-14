"""Reusable meeting intelligence — classification, prep context, no fabricated facts."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Email, Meeting, Opportunity, User, WorkItem
from app.services.agenda_sanitize import detect_recurring, sanitize_agenda
from app.services.email_classification import is_meeting_prep_email
from app.services.mapping_utils import jsonb_or_default, relative_time_label, stringify_id
from app.services.meeting_windows import (
    WINDOW_ORDER,
    classify_meeting_at,
    dedupe_meetings_by_title_start,
    ensure_aware,
    prep_recommended_for_meeting,
    relative_meeting_label,
    short_date_label,
    timing_display_label,
    weekday_date_label,
)
from app.services.time_windows import local_day_bounds, local_today, user_zone

logger = logging.getLogger("briefly.meeting_intelligence")


class MeetingIntelligenceService:
    """Shared meeting timing + lightweight prep context for all product surfaces."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def load_classified_meetings(self, *, include_past: bool = True) -> list[dict[str, Any]]:
        try:
            rows = (
                self.db.query(Meeting)
                .filter(Meeting.user_id == self.user.id)
                .order_by(Meeting.starts_at.asc())
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Could not load meetings for classification", exc_info=True)
            self.db.rollback()
            return []

        rows = dedupe_meetings_by_title_start(rows)
        classified = [self.enrich_meeting_row(row) for row in rows]
        if not include_past:
            classified = [m for m in classified if m["window"] != "past"]
        return classified

    def enrich_meeting_row(self, row: Meeting) -> dict[str, Any]:
        window = classify_meeting_at(row.starts_at, self.user)
        prep_status = row.prep_status or "needs-prep"
        prep_recommended = prep_recommended_for_meeting(
            row.starts_at, prep_status, self.user
        )
        intelligence = jsonb_or_default(row.intelligence)
        company = _normalize_company(jsonb_or_default(row.company))
        google = intelligence.get("google") if isinstance(intelligence.get("google"), dict) else {}
        attendees = _normalize_attendees(row.attendees or [])
        organizer = next(
            (a for a in attendees if (a.get("role") or "").lower() == "organizer"),
            None,
        )
        is_recurring = detect_recurring(intelligence=intelligence) or detect_recurring(
            {"summary": row.title, "description": " ".join(_normalize_agenda(row.agenda))}
        )
        agenda = sanitize_agenda(row.agenda)
        if is_recurring and not agenda:
            agenda = []

        meeting_link = (
            (google.get("htmlLink") if isinstance(google, dict) else None)
            or _extract_meeting_link(row.location)
            or ""
        )

        zone = user_zone(self.user)
        start_local = ensure_aware(row.starts_at).astimezone(zone) if row.starts_at else None
        end_local = ensure_aware(row.ends_at).astimezone(zone) if row.ends_at else None

        return {
            "id": stringify_id(row.id),
            "title": row.title,
            "startsAt": row.starts_at.isoformat() if row.starts_at else None,
            "endsAt": row.ends_at.isoformat() if row.ends_at else None,
            "startTime": start_local.strftime("%H:%M") if start_local else "",
            "endTime": end_local.strftime("%H:%M") if end_local else "",
            "duration": _format_duration(row.starts_at, row.ends_at),
            "dateLabel": short_date_label(row.starts_at, self.user),
            "weekdayDateLabel": weekday_date_label(row.starts_at, self.user),
            "timingLabel": timing_display_label(row.starts_at, self.user),
            "relativeLabel": relative_meeting_label(row.starts_at, self.user),
            "window": window,
            "type": _normalize_meeting_type(row.type),
            "location": row.location or "",
            "meetingLink": meeting_link,
            "organizer": organizer,
            "isRecurring": is_recurring,
            "recurringLabel": "Recurring monthly" if is_recurring else None,
            "prepStatus": prep_status,
            "prepReason": row.prep_reason or "",
            "prepRecommended": prep_recommended,
            "prepStatusLabel": (
                "Prepare today"
                if prep_recommended
                else (
                    "Ready"
                    if window == "today"
                    else "Preparation not yet needed"
                )
            ),
            "attendees": attendees,
            "agenda": agenda,
            "company": company,
            "relatedEmails": intelligence.get("relatedEmails") or [],
            "preparationNotes": intelligence.get("preparationNotes") or [],
            "talkingPoints": intelligence.get("talkingPoints") or [],
            "recommendedQuestions": intelligence.get("recommendedQuestions") or [],
            "risks": intelligence.get("risks") or [],
            "sources": list(row.sources or []),
            "externalId": row.external_id,
            "suggestedPrepActions": [],
            "whyItMatters": None,
            "contextNote": None,
            "prepHighlights": [],
        }

    def group_by_window(self, meetings: list[dict[str, Any]] | None = None) -> dict[str, list[dict]]:
        meetings = meetings if meetings is not None else self.load_classified_meetings()
        groups = {key: [] for key in WINDOW_ORDER}
        for meeting in meetings:
            window = meeting.get("window") or "later"
            if window not in groups:
                window = "later"
            groups[window].append(meeting)
        return groups

    def todays_meetings(self) -> list[dict[str, Any]]:
        return [m for m in self.load_classified_meetings(include_past=False) if m["window"] == "today"]

    def todays_prep_meetings(self) -> list[dict[str, Any]]:
        """Meetings inside the rolling 24h prep horizon that still need prep."""
        return [
            m
            for m in self.load_classified_meetings(include_past=False)
            if m.get("prepRecommended")
        ]

    def this_week_upcoming(self) -> list[dict[str, Any]]:
        """Tomorrow + remainder of this week (not today)."""
        return [
            m
            for m in self.load_classified_meetings(include_past=False)
            if m["window"] in ("tomorrow", "this_week")
        ]

    def build_prep_context(self, meeting: dict[str, Any] | Meeting) -> dict[str, Any]:
        """Deterministic related context for a meeting — never invents facts.

        Full prep treatment only inside the rolling 24h horizon. Other meetings
        get a light upcoming note instead.
        """
        if isinstance(meeting, Meeting):
            data = self.enrich_meeting_row(meeting)
        else:
            data = dict(meeting)

        if not data.get("prepRecommended"):
            return {
                **data,
                "relatedEmailMatches": [],
                "relatedOpportunities": [],
                "relatedWorkItems": [],
                "contextAvailability": {
                    "relatedEmails": 0,
                    "relatedOpportunities": 0,
                    "relatedWorkItems": 0,
                    "hasStoredPrep": False,
                    "contextNote": "Preparation not yet needed — review closer to the meeting.",
                },
                "whyItMatters": (
                    f"Scheduled {data.get('timingLabel') or data.get('relativeLabel') or 'later'} — "
                    "not in the next-24-hour preparation window."
                ),
                "suggestedPrepActions": [
                    "Upcoming — preparation not yet needed.",
                    "Review closer to the meeting.",
                ],
                "prepHighlights": ["Upcoming", "Preparation not yet needed"],
                "prepStatusLabel": "Preparation not yet needed",
            }

        company_name = ""
        company = data.get("company") or {}
        if isinstance(company, dict):
            company_name = (company.get("name") or "").strip()

        title_tokens = _meaningful_tokens(data.get("title") or "")
        attendee_emails = _attendee_emails(data.get("attendees") or [])

        related_emails = self._related_emails(company_name, title_tokens, attendee_emails)
        related_crm = self._related_opportunities(company_name, title_tokens)
        related_work = self._related_work_items(company_name, title_tokens)

        has_prep = bool(
            data.get("preparationNotes")
            or data.get("talkingPoints")
            or data.get("recommendedQuestions")
        )

        limited = not (related_emails or related_crm or related_work or has_prep)
        context_note = (
            "Limited context available — review the meeting agenda before joining."
            if limited
            else _context_note(related_emails, related_crm, related_work, has_prep)
        )

        availability = {
            "relatedEmails": len(related_emails),
            "relatedOpportunities": len(related_crm),
            "relatedWorkItems": len(related_work),
            "hasStoredPrep": has_prep,
            "contextNote": context_note,
        }

        suggested_actions: list[str] = []
        highlights: list[str] = []
        if data.get("prepRecommended"):
            if related_emails:
                suggested_actions.append(
                    f"Review {len(related_emails)} related email thread(s) before the meeting."
                )
                highlights.append(f"{len(related_emails)} related email(s)")
            if related_crm:
                suggested_actions.append(
                    f"Check {len(related_crm)} related CRM opportunit"
                    f"{'y' if len(related_crm) == 1 else 'ies'}."
                )
                highlights.append(
                    f"{len(related_crm)} CRM opportunit{'y' if len(related_crm) == 1 else 'ies'}"
                )
            if related_work:
                suggested_actions.append(
                    f"Scan {len(related_work)} related work item(s) for open blockers."
                )
                highlights.append(f"{len(related_work)} work item(s)")
            if data.get("type") == "client":
                suggested_actions.append("Confirm client-facing talking points and open issues.")
                highlights.append("Client-facing")
            if not suggested_actions:
                suggested_actions.append(
                    "Limited context available — review the meeting agenda before joining."
                )
            if data.get("prepRecommended"):
                highlights.insert(0, "Prepare today")

        why_matters = _why_matters(data, availability)

        return {
            **data,
            "relatedEmailMatches": related_emails,
            "relatedOpportunities": related_crm,
            "relatedWorkItems": related_work,
            "contextAvailability": availability,
            "whyItMatters": why_matters,
            "suggestedPrepActions": suggested_actions,
            "prepHighlights": highlights,
            "contextNote": context_note,
        }

    def focus_items_for_today(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Today's Focus candidates from meetings that recommend prep today only."""
        items = []
        for meeting in self.todays_prep_meetings()[:limit]:
            ctx = self.build_prep_context(meeting)
            items.append(
                {
                    "id": f"focus_meet_{meeting['id']}",
                    "title": meeting["title"] or "Meeting today",
                    "description": ctx["whyItMatters"],
                    "rationale": f"Today · {meeting.get('relativeLabel') or meeting.get('startTime')}",
                    "action": "Open Meetings",
                    "actionTarget": "/meetings",
                    "impact": "needs-prep" if meeting.get("prepRecommended") else "meeting",
                    "priority": "high",
                    "sources": ["Google Calendar"],
                }
            )
        return items

    def _related_emails(
        self, company_name: str, title_tokens: set[str], attendee_emails: set[str]
    ) -> list[dict[str, Any]]:
        day_start, _ = local_day_bounds(self.user)
        try:
            rows = (
                self.db.query(Email)
                .filter(
                    Email.user_id == self.user.id,
                    Email.received_at.isnot(None),
                    Email.received_at >= day_start - timedelta(days=14),
                )
                .order_by(Email.received_at.desc())
                .limit(80)
                .all()
            )
        except SQLAlchemyError:
            self.db.rollback()
            return []

        company_l = company_name.lower()
        matches: list[dict[str, Any]] = []
        for row in rows:
            sender = row.sender if isinstance(row.sender, dict) else {}
            sender_email = (sender.get("email") or "").lower()
            hay = " ".join(
                [
                    row.subject or "",
                    sender.get("name") or "",
                    sender_email,
                ]
            ).lower()
            token_hit = bool(title_tokens and any(t in hay for t in title_tokens))
            company_hit = bool(company_l and company_l in hay)
            attendee_hit = bool(sender_email and sender_email in attendee_emails)
            if not (token_hit or company_hit or attendee_hit):
                continue
            candidate = {
                "id": stringify_id(row.id),
                "subject": row.subject or "(no subject)",
                "sender": sender.get("name") or sender_email or "Unknown",
                "summary": (row.ai_summary or "").strip()
                or "Subject/metadata only — no body summary stored.",
                "time": relative_time_label(row.received_at) if row.received_at else "",
                "category": row.category or "informational",
                "priority": row.priority or "medium",
            }
            if not is_meeting_prep_email(candidate):
                continue
            matches.append(
                {
                    "id": candidate["id"],
                    "subject": candidate["subject"],
                    "sender": candidate["sender"],
                    "summary": candidate["summary"],
                    "time": candidate["time"],
                }
            )
            if len(matches) >= 5:
                break
        return matches

    def _related_opportunities(
        self, company_name: str, title_tokens: set[str]
    ) -> list[dict[str, Any]]:
        company_l = company_name.lower()
        if not company_l and not title_tokens:
            return []
        try:
            rows = (
                self.db.query(Opportunity)
                .filter(Opportunity.user_id == self.user.id)
                .limit(40)
                .all()
            )
        except SQLAlchemyError:
            self.db.rollback()
            return []

        out = []
        for row in rows:
            name = (row.company or row.name or "").lower()
            if company_l and company_l in name:
                out.append(
                    {
                        "id": stringify_id(row.id),
                        "company": row.company or row.name or "",
                        "stage": row.stage or "",
                        "riskLevel": row.risk_level or "",
                    }
                )
            elif title_tokens and any(t in name for t in title_tokens):
                out.append(
                    {
                        "id": stringify_id(row.id),
                        "company": row.company or row.name or "",
                        "stage": row.stage or "",
                        "riskLevel": row.risk_level or "",
                    }
                )
            if len(out) >= 3:
                break
        return out

    def _related_work_items(
        self, company_name: str, title_tokens: set[str]
    ) -> list[dict[str, Any]]:
        if not company_name and not title_tokens:
            return []
        try:
            rows = (
                self.db.query(WorkItem)
                .filter(WorkItem.user_id == self.user.id)
                .order_by(WorkItem.updated_at.desc().nullslast())
                .limit(40)
                .all()
            )
        except SQLAlchemyError:
            self.db.rollback()
            return []

        company_l = company_name.lower()
        out = []
        for row in rows:
            hay = f"{row.title or ''} {row.description or ''} {row.container_name or ''}".lower()
            if company_l and company_l in hay:
                hit = True
            elif title_tokens and any(t in hay for t in title_tokens):
                hit = True
            else:
                hit = False
            if not hit:
                continue
            out.append(
                {
                    "id": stringify_id(row.id),
                    "title": row.title or "Work item",
                    "status": row.status or "",
                    "priority": row.priority or "",
                    "provider": row.provider or "",
                }
            )
            if len(out) >= 3:
                break
        return out


def _format_duration(starts_at: datetime | None, ends_at: datetime | None) -> str:
    if not starts_at or not ends_at:
        return ""
    minutes = int((ends_at - starts_at).total_seconds() // 60)
    return f"{minutes} min"


def _normalize_meeting_type(raw: str | None) -> str:
    value = (raw or "internal").strip().lower()
    if value in ("internal", "client", "investor", "personal"):
        return value
    return "internal"


def _normalize_agenda(agenda: Any) -> list[str]:
    return sanitize_agenda(agenda)


def _extract_meeting_link(location: str | None) -> str:
    text = (location or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return ""


def _normalize_company(company: dict) -> dict[str, Any]:
    return {
        "name": company.get("name") or "",
        "industry": company.get("industry") or "",
        "size": company.get("size") or "",
        "relationship": company.get("relationship") or "",
        "background": company.get("background") or "",
        "arr": company.get("arr"),
    }


def _normalize_attendees(attendees: list) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for attendee in attendees:
        if not isinstance(attendee, dict):
            continue
        name = attendee.get("name") or attendee.get("email") or "Guest"
        avatar = attendee.get("avatar") or "".join(
            part[0] for part in str(name).split()[:2] if part
        ).upper()
        out.append(
            {
                "name": name,
                "role": attendee.get("role") or "",
                "company": attendee.get("company") or "",
                "avatar": avatar or "G",
                "email": attendee.get("email"),
            }
        )
    return out


def _meaningful_tokens(title: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "meeting",
        "call",
        "sync",
        "weekly",
        "monthly",
        "daily",
        "online",
        "program",
        "a",
        "an",
        "of",
        "to",
        "on",
    }
    tokens = re.findall(r"[a-z0-9]{3,}", (title or "").lower())
    return {t for t in tokens if t not in stop}


def _attendee_emails(attendees: list) -> set[str]:
    emails: set[str] = set()
    for attendee in attendees:
        if isinstance(attendee, dict):
            email = (attendee.get("email") or "").strip().lower()
            if email:
                emails.add(email)
    return emails


def _context_note(emails, crm, work, has_prep: bool) -> str:
    if emails or crm or work or has_prep:
        bits = []
        if emails:
            bits.append(f"{len(emails)} related email(s)")
        if crm:
            bits.append(f"{len(crm)} CRM match(es)")
        if work:
            bits.append(f"{len(work)} work item(s)")
        if has_prep:
            bits.append("stored preparation notes")
        return "Available context: " + ", ".join(bits) + "."
    return "Limited context available — review the meeting agenda before joining."


def _why_matters(meeting: dict[str, Any], availability: dict[str, Any]) -> str:
    if meeting.get("window") != "today":
        return (
            f"Scheduled {meeting.get('timingLabel') or meeting.get('relativeLabel') or 'later'} — "
            "not a today preparation item."
        )
    company = meeting.get("company") or {}
    company_name = company.get("name") if isinstance(company, dict) else ""
    parts = []
    if meeting.get("type") == "client" and company_name:
        parts.append(f"Client-facing discussion with {company_name}.")
    elif company_name:
        parts.append(f"Calendar context involves {company_name}.")
    else:
        parts.append(f"On today's calendar at {meeting.get('startTime') or 'TBD'}.")
    if meeting.get("prepRecommended"):
        parts.append("Preparation is recommended before this meeting.")
    parts.append(availability.get("contextNote") or "")
    return " ".join(p for p in parts if p).strip()
