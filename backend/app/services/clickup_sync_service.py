"""Synchronize ClickUp tasks into WorkItem rows."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.clickup import ClickUpClient, ClickUpError, ClickUpUnauthorized
from app.models import Integration, SyncEvent, User, WorkItem
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.clickup_sync")

PROVIDER = "clickup"
SOURCE = "ClickUp"
EXTERNAL_PREFIX = "clickup:"

PRIORITY_MAP = {
    1: "urgent",
    2: "high",
    3: "medium",
    4: "low",
}


class ClickUpSyncService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        integration = self._require_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, PROVIDER)
        client = ClickUpClient(access_token, self.settings)

        meta = dict((integration.config or {}).get("clickup") or {})
        watermark_ms = meta.get("date_updated_watermark_ms")

        try:
            teams = client.list_teams()
            counts = self._sync_teams(user, client, teams, watermark_ms=watermark_ms)
        except ClickUpUnauthorized as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ClickUp authorization expired — reconnect required",
            ) from exc
        except ClickUpError as exc:
            logger.warning("ClickUp sync failed for user %s: %s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        meta["last_sync_reason"] = reason
        meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        meta["team_ids"] = [str(t.get("id")) for t in teams if t.get("id")]
        if counts.get("max_updated_ms") is not None:
            meta["date_updated_watermark_ms"] = counts["max_updated_ms"]
        self._save_meta(integration, meta)
        self._record_sync_event(integration, reason, counts)
        return {
            "upserted": counts.get("upserted", 0),
            "archived": counts.get("archived", 0),
            "teams": counts.get("teams", 0),
            "pages": counts.get("pages", 0),
        }

    def _sync_teams(
        self,
        user: User,
        client: ClickUpClient,
        teams: list[dict[str, Any]],
        *,
        watermark_ms: int | None,
    ) -> dict[str, Any]:
        upserted = 0
        archived = 0
        pages = 0
        max_updated: int | None = watermark_ms
        seen: set[str] = set()

        for team in teams:
            team_id = str(team.get("id") or "")
            if not team_id:
                continue
            team_name = team.get("name") or "Workspace"
            page = 0
            while True:
                payload = client.list_team_tasks(
                    team_id,
                    page=page,
                    include_closed=True,
                    date_updated_gt=watermark_ms,
                    subtasks=True,
                )
                pages += 1
                tasks = payload.get("tasks") or []
                for raw in tasks:
                    if not isinstance(raw, dict):
                        continue
                    updated_ms = _as_int(raw.get("date_updated"))
                    if updated_ms is not None and (
                        max_updated is None or updated_ms > max_updated
                    ):
                        max_updated = updated_ms
                    if self._upsert_task(
                        user,
                        raw,
                        workspace_id=team_id,
                        workspace_name=team_name,
                    ):
                        upserted += 1
                        seen.add(f"{EXTERNAL_PREFIX}{raw.get('id')}")
                    if raw.get("archived"):
                        archived += 1
                # ClickUp returns last_page boolean on filtered team tasks.
                if payload.get("last_page") is True or not tasks:
                    break
                page += 1
                if page > 50:
                    break

        if watermark_ms is None:
            archived += self._archive_missing(user, seen)

        return {
            "upserted": upserted,
            "archived": archived,
            "teams": len(teams),
            "pages": pages,
            "max_updated_ms": max_updated,
        }

    def _upsert_task(
        self,
        user: User,
        raw: dict[str, Any],
        *,
        workspace_id: str,
        workspace_name: str,
    ) -> bool:
        task_id = raw.get("id")
        if not task_id:
            return False
        external_id = f"{EXTERNAL_PREFIX}{task_id}"
        status_obj = raw.get("status") or {}
        status = status_obj.get("status") if isinstance(status_obj, dict) else str(status_obj or "")
        status_type = (
            (status_obj.get("type") or "").lower() if isinstance(status_obj, dict) else ""
        )
        priority_raw = raw.get("priority")
        priority = None
        if isinstance(priority_raw, dict):
            priority = PRIORITY_MAP.get(_as_int(priority_raw.get("id")) or -1) or priority_raw.get(
                "priority"
            )
        elif priority_raw is not None:
            priority = PRIORITY_MAP.get(_as_int(priority_raw) or -1)

        due_at = _ms_to_dt(raw.get("due_date"))
        completed_at = _ms_to_dt(raw.get("date_done") or raw.get("date_closed"))
        if not completed_at and status_type == "closed":
            completed_at = _ms_to_dt(raw.get("date_updated"))

        assignees = raw.get("assignees") or []
        assignee_name = None
        assignee_id = None
        if assignees and isinstance(assignees[0], dict):
            assignee_name = (
                assignees[0].get("username")
                or assignees[0].get("email")
                or assignees[0].get("name")
            )
            assignee_id = str(assignees[0].get("id") or "") or None

        list_obj = raw.get("list") or {}
        folder = raw.get("folder") or {}
        space = raw.get("space") or {}
        container_id = str(list_obj.get("id") or space.get("id") or "")
        container_name = list_obj.get("name") or folder.get("name") or space.get("name")
        parent = raw.get("parent")
        parent_external = f"{EXTERNAL_PREFIX}{parent}" if parent else None
        tags = [
            t.get("name")
            for t in (raw.get("tags") or [])
            if isinstance(t, dict) and t.get("name")
        ]

        existing = (
            self.db.query(WorkItem)
            .filter(
                WorkItem.user_id == user.id,
                WorkItem.provider == PROVIDER,
                WorkItem.external_id == external_id,
            )
            .first()
        )
        if existing is None:
            existing = WorkItem(
                user_id=user.id,
                provider=PROVIDER,
                external_id=external_id,
            )
            self.db.add(existing)

        intelligence = dict(existing.intelligence or {})
        existing.workspace_id = workspace_id
        existing.workspace_name = workspace_name
        existing.container_id = container_id or existing.container_id
        existing.container_name = container_name or existing.container_name
        existing.title = (raw.get("name") or existing.title or "Untitled")[:500]
        description = (raw.get("description") or raw.get("text_content") or "").strip()
        if description:
            existing.description = description[:4000]
        existing.status = (status or existing.status or "")[:100] or None
        existing.priority = (str(priority) if priority else existing.priority)
        existing.due_at = due_at
        existing.completed_at = completed_at
        existing.assignee_name = assignee_name
        existing.assignee_external_id = assignee_id
        existing.url = raw.get("url") or existing.url
        existing.parent_external_id = parent_external
        existing.labels = tags[:20]
        existing.item_metadata = {
            "list_id": list_obj.get("id"),
            "folder_id": folder.get("id"),
            "space_id": space.get("id"),
            "status_type": status_type,
            "date_updated": raw.get("date_updated"),
        }
        existing.intelligence = intelligence
        existing.archived = bool(raw.get("archived"))
        existing.last_synced_at = datetime.now(timezone.utc)
        sources = list(existing.sources or [])
        if SOURCE not in sources:
            sources.append(SOURCE)
        existing.sources = sources
        self.db.commit()
        return True

    def _archive_missing(self, user: User, seen: set[str]) -> int:
        # Full sync with an empty `seen` set means every prior open row is gone.
        rows = (
            self.db.query(WorkItem)
            .filter(
                WorkItem.user_id == user.id,
                WorkItem.provider == PROVIDER,
                WorkItem.archived.is_(False),
            )
            .all()
        )
        count = 0
        for row in rows:
            if row.external_id not in seen:
                row.archived = True
                count += 1
        if count:
            self.db.commit()
        return count

    def _require_integration(self, user: User) -> Integration:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == PROVIDER,
                Integration.status == "connected",
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ClickUp is not connected",
            )
        return row

    def _save_meta(self, integration: Integration, meta: dict[str, Any]) -> None:
        config = dict(integration.config or {})
        config["clickup"] = meta
        integration.config = config
        integration.last_sync_at = datetime.now(timezone.utc)
        integration.status = "connected"
        self.db.commit()

    def _record_sync_event(
        self, integration: Integration, reason: str, counts: dict[str, Any]
    ) -> None:
        detail = (
            f"ClickUp sync ({reason}): "
            f"{counts.get('upserted', 0)} upserted, "
            f"{counts.get('archived', 0)} archived across "
            f"{counts.get('teams', 0)} workspaces"
        )
        self.db.add(
            SyncEvent(
                integration_id=integration.id,
                event="ClickUp sync",
                status="success",
                detail=detail,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ms_to_dt(value: Any) -> datetime | None:
    ms = _as_int(value)
    if ms is None:
        return None
    # ClickUp dates are millisecond epoch strings; accept seconds too.
    seconds = ms / 1000.0 if ms > 10_000_000_000 else float(ms)
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
