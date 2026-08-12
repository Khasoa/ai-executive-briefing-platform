"""AI orchestration — the only service that talks to OpenAI.

Domain services call `AIService` methods. On any provider failure this layer
returns `None` so callers can fall back to curated/demo behaviour unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.openai import (
    OpenAIBadResponse,
    OpenAIClient,
    OpenAIError,
    OpenAINotConfigured,
    OpenAIRateLimit,
    OpenAITimeout,
    OpenAIUnavailable,
)
from app.models import DailyBrief, MorningBrief, User
from app.services import ai_prompts
from app.services.crm_service import CRMService
from app.services.inbox_service import InboxService
from app.services.integration_service import IntegrationService
from app.services.meeting_service import MeetingService
from app.services.mapping_utils import jsonb_or_default
from app.services.settings_service import SettingsService

logger = logging.getLogger("briefly.ai")


class AIService:
    """Single orchestration layer for every AI capability."""

    def __init__(
        self,
        db: Session,
        user: User,
        client: OpenAIClient | None = None,
    ) -> None:
        self.db = db
        self.user = user
        self.client = client or OpenAIClient()

    # -- public capabilities -------------------------------------------------

    def generate_morning_brief_content(self) -> dict[str, Any] | None:
        """Structured Morning Brief content, or None → curated failover."""
        context = self._morning_brief_context()
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.morning_brief_user_prompt(context),
            schema_name="morning_brief",
            schema=ai_prompts.MORNING_BRIEF_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_morning_brief(raw)

    def generate_meeting_prep(self, meeting_context: dict[str, Any]) -> dict[str, Any] | None:
        """Meeting intelligence payload for `Meeting.intelligence`, or None."""
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.meeting_prep_user_prompt(meeting_context),
            schema_name="meeting_prep",
            schema=ai_prompts.MEETING_PREP_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_meeting_prep(raw)

    def generate_email_summary(self, email_context: dict[str, Any]) -> dict[str, Any] | None:
        """Email AI fields (summary / importance / follow-up), or None."""
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.email_summary_user_prompt(email_context),
            schema_name="email_summary",
            schema=ai_prompts.EMAIL_SUMMARY_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_email_summary(raw)

    def generate_email_follow_up(self, email_context: dict[str, Any]) -> dict[str, Any] | None:
        """n8n email triage — structured action/priority JSON, or None on failure."""
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.email_follow_up_user_prompt(email_context),
            schema_name="email_follow_up",
            schema=ai_prompts.EMAIL_FOLLOW_UP_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_email_follow_up(raw)

    def answer_question(self, question: str) -> dict[str, Any] | None:
        """Ask report body (without id / answeredAt), or None → curated."""
        context = self._ask_context()
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.ask_user_prompt(question, context),
            schema_name="ask_report",
            schema=ai_prompts.ASK_REPORT_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_ask_report(raw)

    def generate_weekly_digest(self, email_context: dict[str, Any]) -> dict[str, Any] | None:
        """Cross-system weekly intelligence, or None → curated failover."""
        raw = self._generate_json(
            system=ai_prompts.SYSTEM_EXECUTIVE,
            user=ai_prompts.weekly_digest_user_prompt(email_context),
            schema_name="weekly_digest",
            schema=ai_prompts.WEEKLY_DIGEST_SCHEMA,
        )
        if raw is None:
            return None
        return self._normalise_weekly_digest(raw)

    # -- provider call + failover -------------------------------------------

    def _generate_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            return self.client.generate_json(
                system=system,
                user=user,
                schema_name=schema_name,
                schema=schema,
            )
        except (
            OpenAINotConfigured,
            OpenAITimeout,
            OpenAIRateLimit,
            OpenAIUnavailable,
            OpenAIBadResponse,
            OpenAIError,
        ) as exc:
            logger.warning("OpenAI failover (%s): %s", type(exc).__name__, exc)
            return None
        except Exception:
            logger.warning("OpenAI unexpected failure — curated failover", exc_info=True)
            return None

    # -- context gathering (read-only; no nested AI enrichment) -------------

    def _morning_brief_context(self) -> dict[str, Any]:
        from app.services.meeting_intelligence import MeetingIntelligenceService

        intel = MeetingIntelligenceService(self.db, self.user)
        classified = intel.load_classified_meetings(include_past=False)
        today_meetings = [m for m in classified if m.get("window") == "today"]
        prep_today = [m for m in today_meetings if m.get("prepRecommended")]
        this_week = [
            m for m in classified if m.get("window") in ("tomorrow", "this_week")
        ]
        later = [m for m in classified if m.get("window") in ("this_month", "later")]

        emails = InboxService(self.db, self.user).list_emails()
        opportunities = CRMService(self.db, self.user).list_opportunities()
        integrations = IntegrationService(self.db, self.user).list_integrations()
        preferences = SettingsService(self.db, self.user)._preferences()
        daily = None
        existing = None
        try:
            daily = (
                self.db.query(DailyBrief)
                .filter(DailyBrief.user_id == self.user.id)
                .order_by(DailyBrief.generated_at.desc())
                .first()
            )
            existing = (
                self.db.query(MorningBrief)
                .filter(MorningBrief.user_id == self.user.id)
                .order_by(MorningBrief.generated_at.desc())
                .first()
            )
        except Exception:
            logger.debug("Could not load brief context rows", exc_info=True)

        from collections import Counter

        from app.services.time_windows import local_today, overnight_bounds

        overnight_start, overnight_end = overnight_bounds(self.user)
        overnight_email_count = 0
        try:
            from app.models import Email as EmailModel

            overnight_email_count = (
                self.db.query(EmailModel)
                .filter(
                    EmailModel.user_id == self.user.id,
                    EmailModel.received_at.isnot(None),
                    EmailModel.received_at >= overnight_start,
                    EmailModel.received_at <= overnight_end,
                )
                .count()
            )
        except Exception:
            logger.debug("Could not count overnight emails", exc_info=True)

        senders = Counter()
        for email in emails[:80]:
            sender = email.get("sender") or {}
            senders[(sender.get("name") or sender.get("email") or "Unknown")] += 1

        def _meeting_sample(rows: list[dict], limit: int = 6) -> list[dict]:
            return [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "startTime": m.get("startTime"),
                    "endTime": m.get("endTime"),
                    "startsAt": m.get("startsAt"),
                    "window": m.get("window"),
                    "relativeLabel": m.get("relativeLabel"),
                    "type": m.get("type"),
                    "prepStatus": m.get("prepStatus"),
                    "prepRecommended": m.get("prepRecommended"),
                    "prepReason": m.get("prepReason"),
                    "attendees": m.get("attendees"),
                    "company": m.get("company"),
                }
                for m in rows[:limit]
            ]

        activity_digest = {
            "localDate": local_today(self.user).isoformat(),
            "timezone": self.user.timezone or "UTC",
            "emailCount": len(emails),
            "overnightEmailCount": overnight_email_count,
            "unreadCount": sum(1 for e in emails if e.get("unread")),
            "meetingsTodayCount": len(today_meetings),
            "meetingsNeedingPrepToday": len(prep_today),
            "meetingsThisWeekCount": len(this_week),
            "meetingsLaterCount": len(later),
            "meetingCount": len(today_meetings),
            "topSenders": [{"name": n, "count": c} for n, c in senders.most_common(5)],
            "hasUrgentSignals": any(
                e.get("priority") in ("critical", "high")
                or e.get("category") in ("needs-reply",)
                for e in emails[:40]
            )
            or bool(prep_today),
        }

        return {
            "executive": {
                "name": self.user.full_name or self.user.name,
                "role": self.user.role,
                "company": self.user.company,
                "timezone": self.user.timezone,
            },
            "preferences": preferences,
            "activityDigest": activity_digest,
            "meetingsToday": _meeting_sample(today_meetings),
            "meetingsNeedingPrepToday": _meeting_sample(prep_today),
            "meetingsThisWeek": _meeting_sample(this_week),
            "meetingsLater": _meeting_sample(later, limit=4),
            # Backward-compatible sample — today first, then this week only.
            "meetings": _meeting_sample(today_meetings + this_week, limit=8),
            "emails": [
                {
                    "id": e["id"],
                    "subject": e["subject"],
                    "sender": e["sender"],
                    "priority": e["priority"],
                    "category": e["category"],
                    "aiSummary": (e.get("aiSummary") or "")[:200],
                    "unread": e["unread"],
                    "timeLabel": e["timeLabel"],
                    "hasBodySummary": bool((e.get("aiSummary") or "").strip()),
                }
                for e in emails[:12]
            ],
            "crm": [
                {
                    "id": o["id"],
                    "company": o.get("company") or o.get("name"),
                    "stage": o.get("stage"),
                    "value": o.get("value"),
                    "riskLevel": o.get("riskLevel"),
                    "closeDate": o.get("closeDate"),
                    "owner": o.get("owner"),
                    "lastInteraction": o.get("lastInteraction"),
                    "sources": o.get("sources") or [],
                }
                for o in opportunities[:12]
            ],
            "crmSignals": self._crm_signals(opportunities),
            "integrations": [
                {
                    "id": i["id"],
                    "name": i["name"],
                    "status": i["status"],
                    "lastSyncLabel": i.get("lastSyncLabel"),
                }
                for i in integrations
            ],
            "existingDailyBrief": (
                {
                    "summary": daily.summary,
                    "priorities": jsonb_or_default(daily.priorities),
                    "risks": jsonb_or_default(daily.risks),
                    "executiveScore": daily.executive_score,
                }
                if daily is not None
                else None
            ),
            "previousMorningBrief": (
                {
                    "headline": existing.headline,
                    "executive_summary": existing.executive_summary,
                    "brief_date": str(existing.brief_date),
                }
                if existing is not None
                else None
            ),
            "notion": self._notion_context(),
            "workItems": self._work_items_context(),
        }

    def _crm_signals(self, opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            from app.services.crm_intelligence import derive_crm_signals

            return derive_crm_signals(opportunities)
        except Exception:
            logger.debug("Could not derive CRM signals", exc_info=True)
            return {
                "dealsAtRisk": [],
                "staleOpportunities": [],
                "upcomingCloses": [],
                "followUpRequired": [],
                "highValueNeedingAttention": [],
            }

    def _notion_context(self) -> dict[str, Any]:
        """Outstanding tasks, deadlines, projects, decisions, blocked work."""
        empty = {
            "connected": False,
            "outstandingTasks": [],
            "todaysDeadlines": [],
            "recentProjects": [],
            "decisions": [],
            "blocked": [],
        }
        try:
            from app.services.notion_service import NotionService

            notion = NotionService(self.db)
            if not notion.is_connected(self.user):
                return empty
            return {
                "connected": True,
                "outstandingTasks": notion.to_context_dicts(
                    notion.outstanding_tasks(self.user, limit=15)
                ),
                "todaysDeadlines": notion.to_context_dicts(
                    notion.todays_deadlines(self.user), limit=10
                ),
                "recentProjects": notion.to_context_dicts(
                    notion.recently_updated_projects(self.user, limit=8)
                ),
                "decisions": notion.to_context_dicts(
                    notion.important_decisions(self.user, limit=8)
                ),
                "blocked": notion.to_context_dicts(
                    notion.blocked_work(self.user, limit=10)
                ),
            }
        except Exception:
            logger.debug("Could not load Notion context", exc_info=True)
            return empty

    def _work_items_context(self) -> dict[str, Any]:
        """Normalized monday.com / ClickUp signals for executive AI context."""
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
            from app.services.work_item_service import WorkItemService

            service = WorkItemService(self.db)
            if not service.is_any_connected(self.user):
                return empty
            return service.executive_summary_signals(self.user)
        except Exception:
            logger.debug("Could not load work-items context", exc_info=True)
            return empty

    def _ask_context(self) -> dict[str, Any]:
        context = self._morning_brief_context()
        # Trim for Ask latency — keep the same retrieval sources, fewer rows.
        context["meetings"] = context["meetings"][:8]
        context["emails"] = context["emails"][:12]
        context["crm"] = context["crm"][:8]
        notion = context.get("notion") or {}
        if isinstance(notion, dict):
            context["notion"] = {
                **notion,
                "outstandingTasks": (notion.get("outstandingTasks") or [])[:10],
                "todaysDeadlines": (notion.get("todaysDeadlines") or [])[:8],
                "recentProjects": (notion.get("recentProjects") or [])[:6],
                "decisions": (notion.get("decisions") or [])[:6],
                "blocked": (notion.get("blocked") or [])[:8],
            }
        work = context.get("workItems") or {}
        if isinstance(work, dict):
            context["workItems"] = {
                **work,
                "overdue": (work.get("overdue") or [])[:8],
                "dueSoon": (work.get("dueSoon") or [])[:8],
                "highPriority": (work.get("highPriority") or [])[:8],
                "blocked": (work.get("blocked") or [])[:6],
                "completedThisWeek": (work.get("completedThisWeek") or [])[:6],
                "ownership": (work.get("ownership") or [])[:5],
            }
        return context

    # -- normalisation / light validation -----------------------------------

    @staticmethod
    def _normalise_morning_brief(raw: dict[str, Any]) -> dict[str, Any] | None:
        required = (
            "headline",
            "executive_summary",
            "confidence",
            "sources",
            "priorities",
            "risks",
            "clients",
            "focus",
            "delegation",
            "closing",
            "checklist",
        )
        if any(key not in raw for key in required):
            logger.warning("Morning brief JSON missing required keys")
            return None
        if not isinstance(raw["focus"], dict) or not isinstance(raw["closing"], dict):
            return None
        if not isinstance(raw["checklist"], list):
            return None
        # Ensure OpenAI is attributed when we used the model.
        sources = list(raw["sources"] or [])
        if "OpenAI" not in sources:
            sources.append("OpenAI")
        return {
            "headline": str(raw["headline"]),
            "executive_summary": str(raw["executive_summary"]),
            "confidence": str(raw["confidence"]),
            "sources": sources,
            "sections": {
                "priorities": raw["priorities"] or [],
                "risks": raw["risks"] or [],
                "clients": raw["clients"] or [],
                "focus": raw["focus"],
                "delegation": raw["delegation"] or [],
            },
            "closing": raw["closing"],
            "checklist": [
                {
                    "label": item["label"],
                    "category": item["category"],
                    "due": item["due"],
                    "done": bool(item.get("done", False)),
                }
                for item in raw["checklist"]
                if isinstance(item, dict) and "label" in item
            ],
        }

    @staticmethod
    def _normalise_meeting_prep(raw: dict[str, Any]) -> dict[str, Any] | None:
        required = (
            "executiveSummary",
            "talkingPoints",
            "negotiationStrategy",
            "risks",
            "questionsToAsk",
            "followUpRecommendations",
            "prepReason",
        )
        if any(key not in raw for key in required):
            return None
        notes = [str(raw["executiveSummary"]).strip()]
        strategy = str(raw["negotiationStrategy"]).strip()
        if strategy:
            notes.append(f"Negotiation strategy: {strategy}")
        for item in raw.get("followUpRecommendations") or []:
            if item:
                notes.append(str(item))
        return {
            "preparationNotes": [n for n in notes if n],
            "talkingPoints": [str(x) for x in (raw.get("talkingPoints") or [])],
            "recommendedQuestions": [str(x) for x in (raw.get("questionsToAsk") or [])],
            "risks": [
                {
                    "title": str(r.get("title", "")),
                    "detail": str(r.get("detail", "")),
                    "severity": str(r.get("severity", "medium")),
                }
                for r in (raw.get("risks") or [])
                if isinstance(r, dict)
            ],
            "prepReason": str(raw.get("prepReason") or "AI-prepared from connected context."),
            "aiGenerated": True,
            "manuallyEdited": False,
        }

    @staticmethod
    def _normalise_email_summary(raw: dict[str, Any]) -> dict[str, Any] | None:
        if "summary" not in raw or "importance" not in raw:
            return None
        summary = str(raw["summary"]).strip()
        actions = [str(a).strip() for a in (raw.get("actionItems") or []) if str(a).strip()]
        if actions:
            summary = summary + "\n\nAction items:\n" + "\n".join(f"- {a}" for a in actions)
        return {
            "summary": summary,
            "importance": str(raw.get("importance") or "medium"),
            "followUpSuggestion": str(raw.get("followUpSuggestion") or ""),
            "actionItems": actions,
        }

    @staticmethod
    def _normalise_email_follow_up(raw: dict[str, Any]) -> dict[str, Any] | None:
        required = (
            "requires_action",
            "priority",
            "category",
            "reason",
            "confidence",
        )
        if not isinstance(raw, dict) or any(key not in raw for key in required):
            logger.warning("Email follow-up JSON missing required keys")
            return None

        priority = str(raw.get("priority") or "medium").strip().lower()
        if priority not in ("low", "medium", "high"):
            logger.warning("Email follow-up JSON has invalid priority")
            return None

        try:
            confidence = float(raw.get("confidence"))
        except (TypeError, ValueError):
            logger.warning("Email follow-up JSON has invalid confidence")
            return None
        confidence = max(0.0, min(1.0, confidence))

        def _nullable_str(value: Any) -> str | None:
            if value is None:
                return None
            text = str(value).strip()
            return text or None

        return {
            "requires_action": bool(raw.get("requires_action")),
            "priority": priority,  # type: ignore[dict-item]
            "category": str(raw.get("category") or "other").strip() or "other",
            "action": _nullable_str(raw.get("action")),
            "deadline": _nullable_str(raw.get("deadline")),
            "reason": str(raw.get("reason") or "").strip()
            or "Insufficient information to triage confidently.",
            "suggested_response": _nullable_str(raw.get("suggested_response")),
            "confidence": confidence,
        }

    @staticmethod
    def _normalise_ask_report(raw: dict[str, Any]) -> dict[str, Any] | None:
        required = ("summary", "confidence", "sections", "citations", "followUps")
        if any(key not in raw for key in required):
            return None
        sections = []
        for section in raw.get("sections") or []:
            if not isinstance(section, dict):
                continue
            items = []
            for item in section.get("items") or []:
                if not isinstance(item, dict) or "title" not in item:
                    continue
                items.append(
                    {
                        "title": str(item["title"]),
                        "detail": item.get("detail"),
                        "meta": item.get("meta"),
                    }
                )
            sections.append(
                {
                    "id": str(section.get("id") or "sec"),
                    "title": str(section.get("title") or "Section"),
                    "type": section.get("type") or "list",
                    "items": items,
                    "body": section.get("body"),
                }
            )
        return {
            "summary": str(raw["summary"]),
            "confidence": str(raw["confidence"]),
            "sections": sections,
            "citations": [
                {
                    "source": c.get("source"),
                    "detail": str(c.get("detail", "")),
                    "count": int(c.get("count") or 0),
                }
                for c in (raw.get("citations") or [])
                if isinstance(c, dict) and c.get("source")
            ],
            "followUps": [str(x) for x in (raw.get("followUps") or [])],
        }

    @staticmethod
    def _normalise_weekly_digest(raw: dict[str, Any]) -> dict[str, Any] | None:
        required = (
            "week",
            "headline",
            "summary",
            "important_conversations",
            "decisions_and_approvals",
            "follow_ups",
            "unresolved_items",
            "notable_activity",
            "carry_into_next_week",
            "planning_note",
            "confidence",
            "sources",
        )
        if any(key not in raw for key in required):
            logger.warning("Weekly digest JSON missing required keys")
            return None

        def items(container: dict[str, Any], key: str) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for index, item in enumerate(container.get(key) or []):
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                source = item.get("source") or "Gmail"
                if source not in ai_prompts.SOURCE_ENUM:
                    source = "Gmail"
                kind = item.get("kind") if item.get("kind") in ("fact", "recommendation") else "fact"
                out.append(
                    {
                        "id": str(item.get("id") or f"{key}_{index}"),
                        "title": str(item["title"]),
                        "detail": str(item.get("detail") or ""),
                        "source": source,
                        "emailIds": [str(x) for x in (item.get("emailIds") or []) if x],
                        "kind": kind,
                    }
                )
            return out

        outlook_raw = raw.get("next_week_outlook")
        if not isinstance(outlook_raw, dict):
            outlook_raw = {}
        outlook_keys = (
            "upcoming_meetings",
            "upcoming_deadlines",
            "overdue_work",
            "crm_attention",
            "email_follow_ups",
            "work_items",
            "carry_forward",
            "recommended_priorities",
            "risks_and_watchouts",
            "workload_signals",
        )
        next_week_outlook = {key: items(outlook_raw, key) for key in outlook_keys}

        sources = [s for s in (raw.get("sources") or []) if s in ai_prompts.SOURCE_ENUM]
        if "OpenAI" not in sources:
            sources.append("OpenAI")

        week_summary = str(raw.get("week_summary") or raw.get("summary") or "")
        summary = str(raw.get("summary") or week_summary)

        return {
            "week": str(raw["week"]),
            "headline": str(raw["headline"]),
            "summary": summary,
            "week_summary": week_summary or summary,
            "important_conversations": items(raw, "important_conversations"),
            "decisions_and_approvals": items(raw, "decisions_and_approvals"),
            "follow_ups": items(raw, "follow_ups"),
            "unresolved_items": items(raw, "unresolved_items"),
            "notable_activity": items(raw, "notable_activity"),
            "carry_into_next_week": items(raw, "carry_into_next_week"),
            "next_week_outlook": next_week_outlook,
            "planning_note": str(raw.get("planning_note") or ""),
            "confidence": str(raw.get("confidence") or "medium"),
            "sources": sources,
        }
