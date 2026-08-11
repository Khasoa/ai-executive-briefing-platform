"""Synchronize monday.com board items into WorkItem rows."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.monday import MondayClient, MondayError, MondayUnauthorized
from app.models import Integration, SyncEvent, User, WorkItem
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.monday_sync")

PROVIDER = "monday"
SOURCE = "monday.com"
EXTERNAL_PREFIX = "monday:"


class MondaySyncService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        integration = self._require_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, PROVIDER)
        client = MondayClient(access_token, self.settings)

        meta = dict((integration.config or {}).get("monday") or {})
        watermark = meta.get("items_updated_watermark")
        profile = (integration.config or {}).get("profile") or {}
        workspace_id = str(profile.get("workspace_id") or meta.get("workspace_id") or "")
        workspace_name = str(profile.get("workspace_name") or meta.get("workspace_name") or "")

        try:
            counts = self._sync_boards(
                user,
                client,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                watermark=watermark,
            )
        except MondayUnauthorized as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="monday.com authorization expired — reconnect required",
            ) from exc
        except MondayError as exc:
            logger.warning("monday sync failed for user %s: %s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        meta["workspace_id"] = workspace_id
        meta["workspace_name"] = workspace_name
        meta["last_sync_reason"] = reason
        meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        if counts.get("max_updated_at"):
            meta["items_updated_watermark"] = counts["max_updated_at"]
        self._save_meta(integration, meta)
        self._record_sync_event(integration, reason, counts)
        return {
            "upserted": counts.get("upserted", 0),
            "archived": counts.get("archived", 0),
            "boards": counts.get("boards", 0),
            "pages": counts.get("pages", 0),
        }

    def _sync_boards(
        self,
        user: User,
        client: MondayClient,
        *,
        workspace_id: str,
        workspace_name: str,
        watermark: str | None,
    ) -> dict[str, Any]:
        upserted = 0
        archived = 0
        pages = 0
        boards = client.list_boards(limit=40)
        max_updated: str | None = watermark
        seen_external: set[str] = set()

        for board in boards:
            board_id = str(board.get("id") or "")
            if not board_id:
                continue
            board_name = board.get("name") or "Board"
            board_workspace = str(board.get("workspace_id") or workspace_id or "")
            cursor = None
            while True:
                page = client.list_board_items(board_id, limit=50, cursor=cursor)
                pages += 1
                items = page.get("items") or []
                for raw in items:
                    if not isinstance(raw, dict):
                        continue
                    updated = raw.get("updated_at")
                    if watermark and updated and updated <= watermark:
                        continue
                    if updated and (max_updated is None or updated > max_updated):
                        max_updated = updated
                    if self._upsert_item(
                        user,
                        raw,
                        board_id=board_id,
                        board_name=board_name,
                        workspace_id=board_workspace,
                        workspace_name=workspace_name,
                    ):
                        upserted += 1
                        seen_external.add(f"{EXTERNAL_PREFIX}{raw.get('id')}")
                    if (raw.get("state") or "").lower() == "archived":
                        archived += 1
                cursor = page.get("cursor")
                if not cursor or not items:
                    break

        # Soft-archive open monday items missing from this sync when full (no watermark).
        if not watermark:
            archived += self._archive_missing(user, seen_external)

        return {
            "upserted": upserted,
            "archived": archived,
            "boards": len(boards),
            "pages": pages,
            "max_updated_at": max_updated,
        }

    def _upsert_item(
        self,
        user: User,
        raw: dict[str, Any],
        *,
        board_id: str,
        board_name: str,
        workspace_id: str,
        workspace_name: str,
    ) -> bool:
        item_id = raw.get("id")
        if not item_id:
            return False
        external_id = f"{EXTERNAL_PREFIX}{item_id}"
        columns = raw.get("column_values") or []
        status = _column_text(columns, ("status", "color", "status"))
        priority = _column_text(columns, ("priority",))
        due_at = _parse_due(columns)
        assignee_name, assignee_id = _parse_people(columns)
        description = _column_text(columns, ("long_text", "text", "name")) or ""
        labels = _parse_labels(columns)
        is_archived = (raw.get("state") or "").lower() == "archived"
        completed_at = None
        if status and status.strip().lower() in ("done", "complete", "completed"):
            completed_at = _parse_dt(raw.get("updated_at"))

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
        existing.workspace_id = workspace_id or existing.workspace_id
        existing.workspace_name = workspace_name or existing.workspace_name
        existing.container_id = board_id
        existing.container_name = board_name
        existing.title = (raw.get("name") or existing.title or "Untitled")[:500]
        if description:
            existing.description = description[:4000]
        existing.status = status
        existing.priority = _normalise_priority(priority)
        existing.due_at = due_at
        if completed_at:
            existing.completed_at = completed_at
        elif existing.status and existing.status.strip().lower() not in (
            "done",
            "complete",
            "completed",
        ):
            existing.completed_at = None
        existing.assignee_name = assignee_name
        existing.assignee_external_id = assignee_id
        existing.url = raw.get("url") or existing.url
        existing.labels = labels
        existing.item_metadata = {
            "board_id": board_id,
            "group": (raw.get("group") or {}).get("title"),
            "state": raw.get("state"),
            "updated_at": raw.get("updated_at"),
        }
        existing.intelligence = intelligence
        existing.archived = is_archived
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
                detail="monday.com is not connected",
            )
        return row

    def _save_meta(self, integration: Integration, meta: dict[str, Any]) -> None:
        config = dict(integration.config or {})
        config["monday"] = meta
        integration.config = config
        integration.last_sync_at = datetime.now(timezone.utc)
        integration.status = "connected"
        self.db.commit()

    def _record_sync_event(
        self, integration: Integration, reason: str, counts: dict[str, Any]
    ) -> None:
        detail = (
            f"monday.com sync ({reason}): "
            f"{counts.get('upserted', 0)} upserted, "
            f"{counts.get('archived', 0)} archived across "
            f"{counts.get('boards', 0)} boards"
        )
        self.db.add(
            SyncEvent(
                integration_id=integration.id,
                event="monday.com sync",
                status="success",
                detail=detail,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()


def _column_text(columns: list[Any], types: tuple[str, ...]) -> str | None:
    for col in columns:
        if not isinstance(col, dict):
            continue
        ctype = (col.get("type") or "").lower()
        cid = (col.get("id") or "").lower()
        if ctype in types or cid in types:
            text = (col.get("text") or "").strip()
            if text:
                return text[:100]
    return None


def _parse_due(columns: list[Any]) -> datetime | None:
    for col in columns:
        if not isinstance(col, dict):
            continue
        ctype = (col.get("type") or "").lower()
        if ctype not in ("date", "timeline"):
            continue
        text = (col.get("text") or "").strip()
        if text:
            # monday text often "YYYY-MM-DD" or "YYYY-MM-DD - YYYY-MM-DD"
            first = text.split()[0].split("-")
            if len(first) >= 3 and len(text) >= 10:
                try:
                    return datetime.fromisoformat(text[:10]).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
        value = col.get("value")
        if not value:
            continue
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            date_str = parsed.get("date") or parsed.get("from")
            if date_str:
                try:
                    return datetime.fromisoformat(str(date_str)[:10]).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


def _parse_people(columns: list[Any]) -> tuple[str | None, str | None]:
    for col in columns:
        if not isinstance(col, dict):
            continue
        ctype = (col.get("type") or "").lower()
        if ctype not in ("people", "multiple-person", "person"):
            continue
        text = (col.get("text") or "").strip()
        value = col.get("value")
        person_id = None
        if value:
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                persons = parsed.get("personsAndTeams") or parsed.get("persons_and_teams") or []
                if persons and isinstance(persons[0], dict):
                    person_id = str(persons[0].get("id") or "") or None
        if text:
            return text.split(",")[0].strip()[:255], person_id
    return None, None


def _parse_labels(columns: list[Any]) -> list[str]:
    labels: list[str] = []
    for col in columns:
        if not isinstance(col, dict):
            continue
        if (col.get("type") or "").lower() in ("tags", "label", "dropdown"):
            text = (col.get("text") or "").strip()
            if text:
                labels.extend([p.strip() for p in text.split(",") if p.strip()])
    return labels[:20]


def _normalise_priority(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in ("critical", "urgent", "high", "medium", "low", "normal"):
        if value == "normal":
            return "medium"
        return value
    if "urgent" in value or "critical" in value:
        return "urgent"
    if "high" in value:
        return "high"
    if "medium" in value or "mid" in value:
        return "medium"
    if "low" in value:
        return "low"
    return raw[:40]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None
