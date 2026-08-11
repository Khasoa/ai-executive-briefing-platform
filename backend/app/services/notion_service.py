"""Read API for synced Notion items — used by Overview and AIService."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Integration, NotionItem, User


class NotionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_connected(self, user: User) -> bool:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == "notion",
                Integration.status == "connected",
            )
            .first()
        )
        return row is not None

    def list_items(
        self,
        user: User,
        *,
        kind: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[NotionItem]:
        q = self.db.query(NotionItem).filter(NotionItem.user_id == user.id)
        if not include_archived:
            q = q.filter(NotionItem.archived.is_(False))
        if kind:
            q = q.filter(NotionItem.kind == kind)
        return (
            q.order_by(NotionItem.last_edited_at.desc().nullslast())
            .limit(limit)
            .all()
        )

    def outstanding_tasks(self, user: User, *, limit: int = 20) -> list[NotionItem]:
        done_like = ("done", "complete", "completed", "closed", "archived")
        items = self.list_items(user, kind="task", limit=100)
        open_items = [
            i
            for i in items
            if not i.status or i.status.strip().lower() not in done_like
        ]
        return open_items[:limit]

    def todays_deadlines(self, user: User, *, now: datetime | None = None) -> list[NotionItem]:
        now = now or datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return (
            self.db.query(NotionItem)
            .filter(
                NotionItem.user_id == user.id,
                NotionItem.archived.is_(False),
                NotionItem.due_at.isnot(None),
                NotionItem.due_at >= start,
                NotionItem.due_at < end,
            )
            .order_by(NotionItem.due_at.asc())
            .limit(30)
            .all()
        )

    def overdue(self, user: User, *, now: datetime | None = None, limit: int = 20) -> list[NotionItem]:
        now = now or datetime.now(timezone.utc)
        done_like = ("done", "complete", "completed", "closed")
        rows = (
            self.db.query(NotionItem)
            .filter(
                NotionItem.user_id == user.id,
                NotionItem.archived.is_(False),
                NotionItem.due_at.isnot(None),
                NotionItem.due_at < now,
                NotionItem.kind.in_(("task", "project")),
            )
            .order_by(NotionItem.due_at.asc())
            .limit(80)
            .all()
        )
        return [
            r
            for r in rows
            if not r.status or r.status.strip().lower() not in done_like
        ][:limit]

    def recently_updated_projects(self, user: User, *, limit: int = 10) -> list[NotionItem]:
        return self.list_items(user, kind="project", limit=limit)

    def important_decisions(self, user: User, *, limit: int = 10) -> list[NotionItem]:
        return self.list_items(user, kind="decision", limit=limit)

    def blocked_work(self, user: User, *, limit: int = 15) -> list[NotionItem]:
        items = self.list_items(user, kind="task", limit=80)
        blocked: list[NotionItem] = []
        for item in items:
            blob = f"{item.title} {item.status or ''} {item.content_preview or ''}".lower()
            if "block" in blob or (item.status and "block" in item.status.lower()):
                blocked.append(item)
        return blocked[:limit]

    def recently_edited_documents(self, user: User, *, limit: int = 10) -> list[NotionItem]:
        return (
            self.db.query(NotionItem)
            .filter(
                NotionItem.user_id == user.id,
                NotionItem.archived.is_(False),
                NotionItem.kind.in_(("note", "meeting_notes", "decision", "database")),
            )
            .order_by(NotionItem.last_edited_at.desc().nullslast())
            .limit(limit)
            .all()
        )

    def to_context_dicts(self, items: list[NotionItem], *, limit: int = 20) -> list[dict]:
        out: list[dict] = []
        for item in items[:limit]:
            out.append(
                {
                    "id": item.id,
                    "kind": item.kind,
                    "title": item.title,
                    "status": item.status,
                    "due_at": item.due_at.isoformat() if item.due_at else None,
                    "url": item.url,
                    "preview": (item.content_preview or "")[:500],
                    "last_edited_at": (
                        item.last_edited_at.isoformat() if item.last_edited_at else None
                    ),
                    "source": "Notion",
                }
            )
        return out
