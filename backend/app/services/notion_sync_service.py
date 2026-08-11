"""Synchronize Notion pages/databases into `NotionItem` rows.

NotionService stays read-only: synced rows surface when present; otherwise
demo/curated behaviour is unchanged (empty for non-demo users).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.notion import NotionClient, NotionError, NotionUnauthorized
from app.models import Integration, NotionItem, SyncEvent, User
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.notion_sync")

NOTION_PROVIDER = "notion"
SOURCE = "Notion"


class NotionSyncService:
    """Incremental, idempotent Notion → NotionItem sync."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        integration = self._require_notion_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, NOTION_PROVIDER)
        client = NotionClient(access_token, self.settings)

        meta = dict((integration.config or {}).get("notion") or {})
        watermark = meta.get("last_edited_watermark")
        selected_databases = list(meta.get("selected_database_ids") or [])

        try:
            counts = self._sync_workspace(
                user,
                client,
                watermark=watermark,
                selected_databases=selected_databases,
            )
        except NotionUnauthorized as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Notion authorization expired — reconnect required",
            ) from exc
        except NotionError as exc:
            logger.warning("Notion sync failed for user %s: %s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        # Advance watermark with a 60s backstep for eventual consistency.
        new_watermark = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        meta["last_edited_watermark"] = new_watermark
        meta["last_sync_reason"] = reason
        meta["selected_database_ids"] = selected_databases or meta.get("discovered_database_ids") or []
        self._save_notion_meta(integration, meta)
        self._record_sync_event(integration, reason, counts)
        return counts

    def _sync_workspace(
        self,
        user: User,
        client: NotionClient,
        *,
        watermark: str | None,
        selected_databases: list[str],
    ) -> dict[str, int]:
        upserted = 0
        deleted = 0
        pages = 0
        discovered_dbs: list[str] = []

        # 1) Discover databases shared with the integration.
        cursor = None
        while True:
            payload = client.search(filter_object="database", start_cursor=cursor)
            pages += 1
            for item in payload.get("results") or []:
                if item.get("object") != "database":
                    continue
                db_id = item.get("id")
                if db_id:
                    discovered_dbs.append(db_id)
                if self._upsert_from_notion_object(user, item, client, fetch_preview=False):
                    upserted += 1
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")

        # Persist discovered databases for UI / future selection.
        integration = self._require_notion_integration(user)
        meta = dict((integration.config or {}).get("notion") or {})
        meta["discovered_database_ids"] = discovered_dbs
        if not selected_databases:
            selected_databases = list(discovered_dbs)
            meta["selected_database_ids"] = selected_databases
        self._save_notion_meta(integration, meta)

        # 2) Incremental search across pages (and database rows as pages).
        cursor = None
        while True:
            payload = client.search(filter_object="page", start_cursor=cursor)
            pages += 1
            stop = False
            for item in payload.get("results") or []:
                edited = item.get("last_edited_time")
                if watermark and edited and edited <= watermark:
                    stop = True
                    break
                if item.get("archived"):
                    if self._mark_archived(user, item.get("id")):
                        deleted += 1
                    continue
                if self._upsert_from_notion_object(user, item, client, fetch_preview=True):
                    upserted += 1
            if stop or not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")

        # 3) Query selected databases with last_edited_time filter when watermark set.
        for database_id in selected_databases:
            filter_body = None
            if watermark:
                filter_body = {
                    "timestamp": "last_edited_time",
                    "last_edited_time": {"on_or_after": watermark},
                }
            cursor = None
            while True:
                payload = client.query_database(
                    database_id,
                    start_cursor=cursor,
                    filter_body=filter_body,
                )
                pages += 1
                for item in payload.get("results") or []:
                    if item.get("archived"):
                        if self._mark_archived(user, item.get("id")):
                            deleted += 1
                        continue
                    if self._upsert_from_notion_object(
                        user, item, client, fetch_preview=True, parent_database_id=database_id
                    ):
                        upserted += 1
                if not payload.get("has_more"):
                    break
                cursor = payload.get("next_cursor")

        return {"upserted": upserted, "deleted": deleted, "pages": pages}

    def _upsert_from_notion_object(
        self,
        user: User,
        raw: dict[str, Any],
        client: NotionClient,
        *,
        fetch_preview: bool,
        parent_database_id: str | None = None,
    ) -> bool:
        external_id = raw.get("id")
        if not external_id:
            return False

        object_type = raw.get("object") or "page"
        title = _extract_title(raw)
        props = raw.get("properties") or {}
        status = _extract_status(props)
        due_at = _extract_due(props)
        kind = _classify_kind(object_type, title, props, status)
        url = raw.get("url")
        edited = _parse_dt(raw.get("last_edited_time"))
        parent = raw.get("parent") or {}
        parent_db = parent_database_id or parent.get("database_id")

        preview = ""
        if fetch_preview and object_type == "page":
            preview = self._safe_preview(client, external_id)

        existing = (
            self.db.query(NotionItem)
            .filter(NotionItem.user_id == user.id, NotionItem.external_id == external_id)
            .first()
        )
        if existing is None:
            existing = NotionItem(user_id=user.id, external_id=external_id)
            self.db.add(existing)

        # Preserve AI-generated intelligence.
        intelligence = dict(existing.intelligence or {})

        existing.object_type = object_type
        existing.kind = kind
        existing.title = title or existing.title or "Untitled"
        existing.status = status
        existing.due_at = due_at
        existing.url = url
        existing.parent_database_id = parent_db
        existing.last_edited_at = edited
        existing.archived = bool(raw.get("archived", False))
        existing.properties = _simplify_properties(props)
        if preview:
            existing.content_preview = preview[:4000]
        existing.intelligence = intelligence
        sources = list(existing.sources or [])
        if SOURCE not in sources:
            sources.append(SOURCE)
        existing.sources = sources
        self.db.commit()
        return True

    def _safe_preview(self, client: NotionClient, page_id: str) -> str:
        try:
            payload = client.list_block_children(page_id, page_size=15)
        except NotionError:
            return ""
        chunks: list[str] = []
        for block in payload.get("results") or []:
            text = _block_plain_text(block)
            if text:
                chunks.append(text)
            if sum(len(c) for c in chunks) > 1500:
                break
        return "\n".join(chunks)[:2000]

    def _mark_archived(self, user: User, external_id: str | None) -> bool:
        if not external_id:
            return False
        row = (
            self.db.query(NotionItem)
            .filter(NotionItem.user_id == user.id, NotionItem.external_id == external_id)
            .first()
        )
        if row is None:
            return False
        if row.archived:
            return False
        row.archived = True
        self.db.commit()
        return True

    def _require_notion_integration(self, user: User) -> Integration:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == NOTION_PROVIDER,
                Integration.status == "connected",
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Notion is not connected",
            )
        return row

    def _save_notion_meta(self, integration: Integration, meta: dict[str, Any]) -> None:
        config = dict(integration.config or {})
        config["notion"] = meta
        integration.config = config
        integration.last_sync_at = datetime.now(timezone.utc)
        integration.status = "connected"
        self.db.commit()

    def _record_sync_event(
        self, integration: Integration, reason: str, counts: dict[str, int]
    ) -> None:
        detail = (
            f"{reason} · upserted {counts.get('upserted', 0)} · "
            f"archived {counts.get('deleted', 0)} · pages {counts.get('pages', 0)}"
        )
        self.db.add(
            SyncEvent(
                integration_id=integration.id,
                event="Notion sync",
                status="success",
                detail=detail,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()


# -- property / classification helpers ---------------------------------------


def _extract_title(raw: dict[str, Any]) -> str:
    props = raw.get("properties") or {}
    for key in ("Name", "title", "Title", "Task", "Project"):
        if key in props:
            text = _rich_text_to_plain(props[key])
            if text:
                return text
    for value in props.values():
        if isinstance(value, dict) and value.get("type") == "title":
            text = _rich_text_to_plain(value)
            if text:
                return text
    title = raw.get("title")
    if isinstance(title, list):
        return "".join(part.get("plain_text") or "" for part in title).strip()
    return ""


def _rich_text_to_plain(prop: dict[str, Any]) -> str:
    typ = prop.get("type")
    if typ == "title":
        return "".join(p.get("plain_text") or "" for p in prop.get("title") or []).strip()
    if typ == "rich_text":
        return "".join(p.get("plain_text") or "" for p in prop.get("rich_text") or []).strip()
    if typ == "select":
        sel = prop.get("select") or {}
        return (sel.get("name") or "").strip()
    if typ == "status":
        st = prop.get("status") or {}
        return (st.get("name") or "").strip()
    if typ == "multi_select":
        return ", ".join(x.get("name") or "" for x in prop.get("multi_select") or [])
    return ""


def _extract_status(props: dict[str, Any]) -> str | None:
    for key in ("Status", "status", "State"):
        if key in props:
            text = _rich_text_to_plain(props[key])
            if text:
                return text
    for value in props.values():
        if isinstance(value, dict) and value.get("type") in ("status", "select"):
            text = _rich_text_to_plain(value)
            if text:
                return text
    return None


def _extract_due(props: dict[str, Any]) -> datetime | None:
    for key in ("Due", "Due date", "Deadline", "Date"):
        if key not in props:
            continue
        prop = props[key]
        if not isinstance(prop, dict) or prop.get("type") != "date":
            continue
        date = prop.get("date") or {}
        start = date.get("start")
        if start:
            return _parse_dt(start)
    for value in props.values():
        if isinstance(value, dict) and value.get("type") == "date":
            date = value.get("date") or {}
            start = date.get("start")
            if start:
                return _parse_dt(start)
    return None


def _classify_kind(
    object_type: str,
    title: str,
    props: dict[str, Any],
    status: str | None,
) -> str:
    if object_type == "database":
        return "database"
    lower = (title or "").lower()
    prop_keys = " ".join(props.keys()).lower()
    if "decision" in lower:
        return "decision"
    if "meeting" in lower or "notes" in lower and "meeting" in prop_keys:
        return "meeting_notes"
    if any(k in prop_keys for k in ("due", "deadline", "assignee", "status")) or status:
        if "project" in lower or "project" in prop_keys:
            return "project"
        return "task"
    if "project" in lower:
        return "project"
    if re.search(r"\b(blocked|blocker)\b", lower):
        return "task"
    return "note"


def _simplify_properties(props: dict[str, Any]) -> dict[str, Any]:
    simplified: dict[str, Any] = {}
    for key, value in list(props.items())[:40]:
        if not isinstance(value, dict):
            continue
        plain = _rich_text_to_plain(value)
        if plain:
            simplified[key] = plain
        elif value.get("type") == "date":
            date = value.get("date") or {}
            if date.get("start"):
                simplified[key] = date.get("start")
    return simplified


def _block_plain_text(block: dict[str, Any]) -> str:
    typ = block.get("type")
    if not typ:
        return ""
    payload = block.get(typ) or {}
    rich = payload.get("rich_text") or payload.get("text") or []
    if isinstance(rich, list):
        return "".join(p.get("plain_text") or "" for p in rich).strip()
    return ""


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if len(value) == 10:
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
