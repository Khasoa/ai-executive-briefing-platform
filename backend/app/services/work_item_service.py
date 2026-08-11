"""Provider-neutral read API for synced WorkItems (monday.com + ClickUp)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Integration, User, WorkItem

DONE_LIKE = frozenset(
    {
        "done",
        "complete",
        "completed",
        "closed",
        "archived",
        "won",
        "resolved",
    }
)
BLOCKED_TOKENS = ("block", "stuck", "waiting", "on hold", "blocked")
HIGH_PRIORITY = frozenset({"urgent", "high", "critical", "1", "2"})

PROVIDER_LABELS = {
    "monday": "monday.com",
    "clickup": "ClickUp",
}


class WorkItemService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def connected_providers(self, user: User) -> list[str]:
        rows = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider.in_(("monday", "clickup")),
                Integration.status == "connected",
            )
            .all()
        )
        return [r.provider for r in rows]

    def is_any_connected(self, user: User) -> bool:
        return bool(self.connected_providers(user))

    def list_items(
        self,
        user: User,
        *,
        provider: str | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[WorkItem]:
        q = self.db.query(WorkItem).filter(WorkItem.user_id == user.id)
        if provider:
            q = q.filter(WorkItem.provider == provider)
        if not include_archived:
            q = q.filter(WorkItem.archived.is_(False))
        return q.order_by(WorkItem.due_at.asc().nullslast()).limit(limit).all()

    def open_items(self, user: User, *, limit: int = 40) -> list[WorkItem]:
        items = self.list_items(user, limit=200)
        return [i for i in items if not _is_done(i)][:limit]

    def overdue(self, user: User, *, now: datetime | None = None, limit: int = 20) -> list[WorkItem]:
        now = now or datetime.now(timezone.utc)
        rows = (
            self.db.query(WorkItem)
            .filter(
                WorkItem.user_id == user.id,
                WorkItem.archived.is_(False),
                WorkItem.due_at.isnot(None),
                WorkItem.due_at < now,
                WorkItem.completed_at.is_(None),
            )
            .order_by(WorkItem.due_at.asc())
            .limit(80)
            .all()
        )
        return [r for r in rows if not _is_done(r)][:limit]

    def due_soon(
        self,
        user: User,
        *,
        now: datetime | None = None,
        within_days: int = 3,
        limit: int = 20,
    ) -> list[WorkItem]:
        now = now or datetime.now(timezone.utc)
        end = now + timedelta(days=within_days)
        rows = (
            self.db.query(WorkItem)
            .filter(
                WorkItem.user_id == user.id,
                WorkItem.archived.is_(False),
                WorkItem.due_at.isnot(None),
                WorkItem.due_at >= now,
                WorkItem.due_at <= end,
                WorkItem.completed_at.is_(None),
            )
            .order_by(WorkItem.due_at.asc())
            .limit(80)
            .all()
        )
        return [r for r in rows if not _is_done(r)][:limit]

    def high_priority(self, user: User, *, limit: int = 15) -> list[WorkItem]:
        items = self.open_items(user, limit=100)
        return [
            i
            for i in items
            if (i.priority or "").strip().lower() in HIGH_PRIORITY
        ][:limit]

    def blocked(self, user: User, *, limit: int = 15) -> list[WorkItem]:
        items = self.open_items(user, limit=100)
        out: list[WorkItem] = []
        for item in items:
            blob = f"{item.title} {item.status or ''} {item.description or ''}".lower()
            if any(tok in blob for tok in BLOCKED_TOKENS):
                out.append(item)
        return out[:limit]

    def completed_recently(
        self,
        user: User,
        *,
        now: datetime | None = None,
        within_days: int = 7,
        limit: int = 20,
    ) -> list[WorkItem]:
        now = now or datetime.now(timezone.utc)
        start = now - timedelta(days=within_days)
        return (
            self.db.query(WorkItem)
            .filter(
                WorkItem.user_id == user.id,
                WorkItem.completed_at.isnot(None),
                WorkItem.completed_at >= start,
            )
            .order_by(WorkItem.completed_at.desc())
            .limit(limit)
            .all()
        )

    def ownership_concentration(self, user: User, *, limit: int = 8) -> list[dict[str, Any]]:
        items = self.overdue(user, limit=50) + self.high_priority(user, limit=50)
        counts: Counter[str] = Counter()
        for item in items:
            name = (item.assignee_name or "Unassigned").strip() or "Unassigned"
            counts[name] += 1
        return [
            {"assignee": name, "attentionItems": count}
            for name, count in counts.most_common(limit)
            if count >= 2
        ]

    def executive_summary_signals(self, user: User) -> dict[str, Any]:
        overdue = self.overdue(user, limit=20)
        due_soon = self.due_soon(user, limit=20)
        high = self.high_priority(user, limit=15)
        blocked = self.blocked(user, limit=15)
        completed = self.completed_recently(user, limit=20)
        open_items = self.open_items(user, limit=40)
        providers = self.connected_providers(user)
        return {
            "connected": bool(providers),
            "providers": [PROVIDER_LABELS.get(p, p) for p in providers],
            "overdue": self.to_context_dicts(overdue, limit=12),
            "dueSoon": self.to_context_dicts(due_soon, limit=12),
            "highPriority": self.to_context_dicts(high, limit=10),
            "blocked": self.to_context_dicts(blocked, limit=10),
            "completedThisWeek": self.to_context_dicts(completed, limit=10),
            "openCount": len(open_items),
            "overdueCount": len(overdue),
            "ownership": self.ownership_concentration(user),
        }

    @staticmethod
    def to_context_dicts(items: list[WorkItem], *, limit: int = 20) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in items[:limit]:
            source = PROVIDER_LABELS.get(item.provider, item.provider)
            sources = list(item.sources or [])
            if source not in sources:
                sources = [source, *sources]
            out.append(
                {
                    "id": str(item.id),
                    "provider": item.provider,
                    "source": source,
                    "title": item.title,
                    "status": item.status,
                    "priority": item.priority,
                    "dueAt": item.due_at.isoformat() if item.due_at else None,
                    "assignee": item.assignee_name,
                    "project": item.container_name,
                    "workspace": item.workspace_name,
                    "url": item.url,
                    "snippet": (item.description or "")[:200],
                    "sources": sources,
                }
            )
        return out


def _is_done(item: WorkItem) -> bool:
    if item.completed_at is not None:
        return True
    status = (item.status or "").strip().lower()
    return status in DONE_LIKE
