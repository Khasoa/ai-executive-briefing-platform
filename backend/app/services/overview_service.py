import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Email, User
from app.schemas.overview import OverviewResponse
from app.services import demo_data
from app.services.daily_brief_service import DailyBriefService
from app.services.db_fallback import read_with_fallback
from app.services.demo_user import is_demo_user, public_user_dict
from app.services.email_classification import is_executive_priority_email
from app.services.inbox_service import InboxService
from app.services.meeting_intelligence import MeetingIntelligenceService
from app.services.morning_brief_service import MorningBriefService
from app.services.notion_service import NotionService
from app.services.time_windows import overnight_bounds
from app.services.work_item_service import PROVIDER_LABELS, WorkItemService

logger = logging.getLogger("briefly.overview")


class OverviewService:
    """Assembles the executive dashboard from every connected system.

    Phase 1 of the PostgreSQL migration lives here: `summary`, `priorities`
    and `risks` are read from the `daily_briefs` table when a row exists.
    Surfaces prefer Notion, then work tools, then Gmail/Calendar activity.
    Fallback remains demo_data for the demo tenant.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_overview(self) -> OverviewResponse:
        summary, priorities, risks = self._executive_summary_source()
        surface = (
            self._notion_surface()
            or self._work_items_surface()
            or self._google_surface()
        )

        return OverviewResponse(
            user=public_user_dict(self.user),
            brief=MorningBriefService(self.db, self.user).get_brief_meta(),
            executiveSummary={
                "summary": summary,
                "priorities": priorities,
                "risks": risks,
                "meetingsToPrepare": self._meetings_to_prepare(),
                "clientsNeedingAttention": (
                    demo_data.CLIENTS_NEEDING_ATTENTION if is_demo_user(self.user) else []
                ),
                "recommendedActions": (
                    surface["recommendedActions"]
                    if surface
                    else self._recommended_actions()
                ),
            },
            kpis=(
                surface["kpis"]
                if surface
                else (demo_data.KPIS if is_demo_user(self.user) else [])
            ),
            activity=(
                surface["activity"]
                if surface
                else (demo_data.ACTIVITY if is_demo_user(self.user) else [])
            ),
            focus=(
                surface["focus"]
                if surface
                else (demo_data.TODAYS_FOCUS if is_demo_user(self.user) else [])
            ),
        )

    def _executive_summary_source(self) -> tuple[str, list, list]:
        brief = read_with_fallback(
            read=lambda: DailyBriefService(self.db, self.user).get_latest_brief(),
            fallback=None,
            logger=logger,
            label="daily_briefs",
            log_empty=False,
            db=self.db,
        )

        if brief is None:
            if is_demo_user(self.user):
                return demo_data.EXECUTIVE_SUMMARY_TEXT, demo_data.PRIORITIES, demo_data.RISKS
            return "", [], []

        return brief.summary, brief.priorities, brief.risks

    def _meetings_to_prepare(self) -> list[dict]:
        """Only today's meetings that recommend prep — never future calendar items."""
        return [
            {
                "id": meeting["id"],
                "title": meeting["title"],
                "time": meeting.get("startTime") or "",
                "reason": meeting.get("prepReason")
                or meeting.get("whyItMatters")
                or "Preparation recommended for today's meeting",
            }
            for meeting in MeetingIntelligenceService(self.db, self.user).todays_prep_meetings()
        ]

    def _recommended_actions(self) -> list[dict]:
        if not is_demo_user(self.user):
            return []
        return [
            {
                "id": f"act_{item['id']}",
                "label": item["title"],
                "rationale": item["rationale"],
            }
            for item in demo_data.TODAYS_FOCUS
        ]

    def _google_surface(self) -> dict | None:
        """Focus + Overnight from Gmail/Calendar when Notion/work tools are idle.

        Today's Focus meeting rows come only from meetings that recommend prep
        today — a monthly event weeks away never appears as prepare-today.
        """
        intel = MeetingIntelligenceService(self.db, self.user)
        try:
            overnight_start, overnight_end = overnight_bounds(self.user)

            emails = (
                self.db.query(Email)
                .filter(
                    Email.user_id == self.user.id,
                    Email.received_at.isnot(None),
                    Email.received_at >= overnight_start,
                    Email.received_at <= overnight_end,
                )
                .order_by(Email.received_at.desc())
                .limit(12)
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Google overview surface query failed", exc_info=True)
            self.db.rollback()
            return None

        classified = intel.load_classified_meetings(include_past=False)
        today_meetings = [m for m in classified if m.get("window") == "today"]
        week_meetings = [
            m for m in classified if m.get("window") in ("tomorrow", "this_week")
        ]

        if not emails and not classified:
            return None

        focus: list[dict] = list(intel.focus_items_for_today(limit=5))

        email_dicts = [InboxService(self.db, self.user)._to_dict(row) for row in emails]
        meaningful = [e for e in email_dicts if is_executive_priority_email(e)]
        pool = meaningful or [
            e
            for e in email_dicts
            if (e.get("category") or "") not in ("promotional", "newsletter", "automated")
        ] or email_dicts
        for email in pool[:4]:
            sender = email.get("sender") or {}
            focus.append(
                {
                    "id": f"focus_mail_{email['id']}",
                    "title": email.get("subject") or "(no subject)",
                    "description": (email.get("aiSummary") or "").strip()
                    or f"From {sender.get('name') or sender.get('email') or 'Unknown'} — subject/metadata only.",
                    "rationale": email.get("timeLabel") or "Recent email",
                    "action": "Open Inbox",
                    "actionTarget": "/inbox",
                    "impact": email.get("category") or "email",
                    "priority": email.get("priority") or "medium",
                    "sources": ["Gmail"],
                }
            )

        activity = []
        for email in email_dicts[:6]:
            sender = email.get("sender") or {}
            activity.append(
                {
                    "id": f"act_mail_{email['id']}",
                    "type": "email",
                    "title": email.get("subject") or "(no subject)",
                    "detail": f"From {sender.get('name') or sender.get('email') or 'Unknown'}",
                    "time": email.get("timeLabel") or "",
                    "source": "Gmail",
                }
            )
        for meeting in today_meetings[:3]:
            activity.append(
                {
                    "id": f"act_meet_{meeting['id']}",
                    "type": "meeting",
                    "title": meeting.get("title") or "Meeting",
                    "detail": meeting.get("prepReason")
                    or meeting.get("relativeLabel")
                    or "On today's calendar",
                    "time": meeting.get("relativeLabel") or meeting.get("startTime") or "",
                    "source": "Google Calendar",
                }
            )

        unread = sum(1 for e in email_dicts if e.get("unread"))
        kpis = [
            {
                "id": "inbox",
                "label": "Overnight mail",
                "value": str(len(emails)),
                "sublabel": f"{unread} unread" if unread else "synced",
                "change": "last 18h",
                "trend": "up" if emails else "neutral",
                "icon": "inbox",
                "tone": "accent" if unread else "slate",
            },
            {
                "id": "meetings",
                "label": "Meetings today",
                "value": str(len(today_meetings)),
                "sublabel": (
                    f"{len(week_meetings)} later this week"
                    if week_meetings
                    else "calendar"
                ),
                "change": "today",
                "trend": "neutral",
                "icon": "meetings",
                "tone": "accent" if today_meetings else "slate",
            },
        ]
        if is_demo_user(self.user):
            base = [k for k in demo_data.KPIS if k["id"] not in ("inbox", "meetings", "tasks")]
            kpis = base + kpis

        recommended = [
            {"id": f"act_{item['id']}", "label": item["title"], "rationale": item["rationale"]}
            for item in focus[:5]
        ]

        return {
            "focus": focus[:8],
            "activity": activity[:8],
            "kpis": kpis,
            "recommendedActions": recommended,
        }

    def _notion_surface(self) -> dict | None:
        """Build overview slices from synced Notion items, or None to keep legacy paths."""
        notion = NotionService(self.db)
        if not notion.is_connected(self.user):
            return None

        today_tasks = notion.todays_deadlines(self.user)
        outstanding = notion.outstanding_tasks(self.user, limit=20)
        overdue = notion.overdue(self.user, limit=15)
        docs = notion.recently_edited_documents(self.user, limit=8)
        projects = notion.recently_updated_projects(self.user, limit=6)

        if not (today_tasks or outstanding or overdue or docs or projects):
            return None

        # Prefer today's deadlines, then overdue, then other open tasks for focus.
        focus_items = list(today_tasks) + [t for t in overdue if t not in today_tasks]
        for task in outstanding:
            if task not in focus_items:
                focus_items.append(task)
        focus_items = focus_items[:6]

        focus = [
            {
                "id": f"notion_{item.id}",
                "title": item.title,
                "description": (item.content_preview or item.status or "From Notion").strip()[
                    :280
                ],
                "rationale": _notion_rationale(item),
                "action": "Open in Notion",
                "actionTarget": item.url or "/integrations",
                "impact": item.status or item.kind,
                "priority": _notion_priority(item),
                "sources": ["Notion"],
            }
            for item in focus_items
        ]

        # Project status as additional focus rows when space remains.
        for project in projects:
            if len(focus) >= 8:
                break
            if any(f["id"] == f"notion_{project.id}" for f in focus):
                continue
            focus.append(
                {
                    "id": f"notion_{project.id}",
                    "title": f"Project · {project.title}",
                    "description": (project.content_preview or "Recently updated project").strip()[
                        :280
                    ],
                    "rationale": f"Status: {project.status or 'in progress'}",
                    "action": "Review project",
                    "actionTarget": project.url or "/integrations",
                    "impact": project.status or "project",
                    "priority": "medium",
                    "sources": ["Notion"],
                }
            )

        activity = [
            {
                "id": f"notion_act_{item.id}",
                "type": "document",
                "title": item.title,
                "detail": f"{item.kind.replace('_', ' ').title()}"
                + (f" · {item.status}" if item.status else ""),
                "time": _relative_edited(item.last_edited_at),
                "source": "Notion",
            }
            for item in docs[:5]
        ]

        overdue_count = len(overdue)
        open_count = len(outstanding)
        kpis = [
            {
                "id": "tasks",
                "label": "Pending Tasks",
                "value": str(open_count),
                "sublabel": "from Notion",
                "change": f"{overdue_count} overdue" if overdue_count else "none overdue",
                "trend": "down" if overdue_count else "neutral",
                "icon": "tasks",
                "tone": "accent" if overdue_count else "slate",
            }
        ]
        if is_demo_user(self.user):
            # Keep other demo KPIs; replace the tasks tile.
            base = [k for k in demo_data.KPIS if k["id"] != "tasks"]
            kpis = base + kpis

        recommended = [
            {
                "id": f"act_notion_{item.id}",
                "label": item.title,
                "rationale": _notion_rationale(item),
            }
            for item in (today_tasks + overdue + outstanding)[:5]
        ]

        return {
            "focus": focus,
            "activity": activity if activity else (demo_data.ACTIVITY if is_demo_user(self.user) else []),
            "kpis": kpis if len(kpis) > 1 or not is_demo_user(self.user) else demo_data.KPIS,
            "recommendedActions": recommended
            if recommended
            else self._recommended_actions(),
        }

    def _work_items_surface(self) -> dict | None:
        """Overview slices from monday.com / ClickUp WorkItems when Notion is idle."""
        work = WorkItemService(self.db)
        if not work.is_any_connected(self.user):
            return None

        overdue = work.overdue(self.user, limit=15)
        due_soon = work.due_soon(self.user, limit=15)
        high = work.high_priority(self.user, limit=12)
        open_items = work.open_items(self.user, limit=20)
        blocked = work.blocked(self.user, limit=10)

        if not (overdue or due_soon or high or open_items or blocked):
            return None

        # Urgency-first order; id-dedupe (separate queries = different ORM instances).
        focus_pool = _dedupe_work_items_by_id(
            list(overdue) + list(due_soon) + list(high) + list(blocked) + list(open_items)
        )[:8]

        focus = []
        for item in focus_pool:
            source = PROVIDER_LABELS.get(item.provider, item.provider)
            focus.append(
                {
                    "id": f"work_{item.id}",
                    "title": item.title,
                    "description": (
                        item.description
                        or item.status
                        or item.container_name
                        or f"From {source}"
                    ).strip()[:280],
                    "rationale": _work_rationale(item),
                    "action": f"Open in {source}",
                    "actionTarget": item.url or "/integrations",
                    "impact": item.status or item.priority or "task",
                    "priority": _work_priority(item),
                    "sources": [source],
                }
            )

        activity = [
            {
                "id": f"work_act_{item.id}",
                "type": "task",
                "title": item.title,
                "detail": (item.container_name or "Task")
                + (f" · {item.status}" if item.status else ""),
                "time": _relative_edited(item.last_synced_at or item.updated_at),
                "source": PROVIDER_LABELS.get(item.provider, item.provider),
            }
            for item in open_items[:5]
        ]

        overdue_count = len(overdue)
        open_count = len(open_items)
        provider_label = " / ".join(
            PROVIDER_LABELS.get(p, p) for p in work.connected_providers(self.user)
        )
        kpis = [
            {
                "id": "tasks",
                "label": "Pending Tasks",
                "value": str(open_count),
                "sublabel": f"from {provider_label}" if provider_label else "work tools",
                "change": f"{overdue_count} overdue" if overdue_count else "none overdue",
                "trend": "down" if overdue_count else "neutral",
                "icon": "tasks",
                "tone": "accent" if overdue_count else "slate",
            }
        ]
        if is_demo_user(self.user):
            base = [k for k in demo_data.KPIS if k["id"] != "tasks"]
            kpis = base + kpis

        recommended = [
            {
                "id": f"act_work_{item.id}",
                "label": item.title,
                "rationale": _work_rationale(item),
            }
            for item in _dedupe_work_items_by_id(
                list(overdue) + list(due_soon) + list(high) + list(open_items)
            )[:5]
        ]

        return {
            "focus": focus,
            "activity": activity
            if activity
            else (demo_data.ACTIVITY if is_demo_user(self.user) else []),
            "kpis": kpis if len(kpis) > 1 or not is_demo_user(self.user) else demo_data.KPIS,
            "recommendedActions": recommended if recommended else self._recommended_actions(),
        }


def _dedupe_work_items_by_id(items: list) -> list:
    """Keep urgency-bucket order; drop later repeats of the same WorkItem.id."""
    seen: set = set()
    out: list = []
    for item in items:
        key = getattr(item, "id", None)
        if key is None or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _work_rationale(item) -> str:
    bits = []
    if item.due_at:
        bits.append(f"Due {item.due_at.astimezone(timezone.utc).strftime('%Y-%m-%d')}")
    if item.assignee_name:
        bits.append(item.assignee_name)
    if item.status:
        bits.append(item.status)
    if item.priority:
        bits.append(f"{item.priority} priority")
    return " · ".join(bits) if bits else (item.container_name or "Work item")


def _work_priority(item) -> str:
    now = datetime.now(timezone.utc)
    if item.due_at and item.due_at < now:
        return "critical"
    priority = (item.priority or "").lower()
    if priority in ("urgent", "critical", "high"):
        return "high"
    if item.due_at and item.due_at.date() == now.date():
        return "high"
    status = (item.status or "").lower()
    if "block" in status:
        return "high"
    return "medium"


def _notion_rationale(item) -> str:
    if item.due_at:
        due = item.due_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        return f"Due {due}" + (f" · {item.status}" if item.status else "")
    if item.status:
        return f"Status: {item.status}"
    return f"Notion {item.kind.replace('_', ' ')}"


def _notion_priority(item) -> str:
    now = datetime.now(timezone.utc)
    if item.due_at and item.due_at < now:
        return "critical"
    if item.due_at and item.due_at.date() == now.date():
        return "high"
    status = (item.status or "").lower()
    if "block" in status:
        return "high"
    return "medium"


def _relative_edited(value: datetime | None) -> str:
    if value is None:
        return "Recently"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - value
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 1)}m ago"
    hours = minutes // 60
    if hours < 36:
        return f"{hours}h ago"
    return value.astimezone(timezone.utc).strftime("%b %d")
