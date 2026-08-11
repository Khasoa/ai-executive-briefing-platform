"""n8n orchestration helpers — sync providers + regenerate briefs without business logic in n8n."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import User
from app.services.demo_user import get_or_create_demo_user

logger = logging.getLogger("briefly.orchestration")

ALL_PROVIDERS = (
    "google-calendar",
    "gmail",
    "notion",
    "gohighlevel",
    "monday",
    "clickup",
)


class OrchestrationService:
    """Runs scheduled sync/regenerate steps with per-step failure isolation."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def resolve_user(
        self,
        *,
        user_id: str | None = None,
        user_email: str | None = None,
    ) -> User:
        if user_id:
            try:
                uid = UUID(user_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid userId",
                ) from exc
            user = self.db.get(User, uid)
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            return user

        if user_email:
            user = (
                self.db.query(User)
                .filter(User.email == user_email.strip().lower())
                .first()
            )
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            return user

        # Portfolio / scheduled default: demo executive.
        return get_or_create_demo_user(self.db)

    def run(
        self,
        user: User,
        *,
        sync_providers: list[str] | None = None,
        regenerate_morning_brief: bool = False,
        regenerate_weekly_digest: bool = False,
    ) -> dict[str, Any]:
        providers = sync_providers if sync_providers is not None else list(ALL_PROVIDERS)
        started = datetime.now(timezone.utc)
        steps: list[dict[str, Any]] = []

        for provider in providers:
            steps.append(self._sync_provider(user, provider))

        if regenerate_morning_brief:
            steps.append(self._regenerate_morning_brief(user))

        if regenerate_weekly_digest:
            steps.append(self._regenerate_weekly_digest(user))

        failed = [s for s in steps if s.get("status") == "error"]
        succeeded = [s for s in steps if s.get("status") == "success"]
        skipped = [s for s in steps if s.get("status") == "skipped"]

        result = {
            "ok": len(failed) == 0,
            "partial": bool(failed) and bool(succeeded),
            "startedAt": started.isoformat(),
            "finishedAt": datetime.now(timezone.utc).isoformat(),
            "userId": str(user.id),
            "userEmail": user.email,
            "steps": steps,
            "summary": {
                "success": len(succeeded),
                "skipped": len(skipped),
                "error": len(failed),
            },
        }
        logger.info(
            "n8n orchestration finished user=%s success=%s errors=%s",
            user.email,
            len(succeeded),
            len(failed),
        )
        return result

    def _sync_provider(self, user: User, provider: str) -> dict[str, Any]:
        key = provider.strip().lower()
        try:
            if key in ("google-calendar", "google"):
                from app.services.calendar_sync_service import CalendarSyncService

                counts = CalendarSyncService(self.db).sync_user(user, reason="n8n")
                return _ok(key, "sync", counts)
            if key == "gmail":
                from app.services.gmail_sync_service import GmailSyncService

                counts = GmailSyncService(self.db).sync_user(user, reason="n8n")
                return _ok(key, "sync", counts)
            if key == "notion":
                from app.services.notion_sync_service import NotionSyncService

                counts = NotionSyncService(self.db).sync_user(user, reason="n8n")
                return _ok(key, "sync", counts)
            if key in ("gohighlevel", "ghl"):
                from app.services.ghl_sync_service import GHLSyncService

                counts = GHLSyncService(self.db).sync_user(user, reason="n8n")
                return _ok("gohighlevel", "sync", counts)
            if key == "monday":
                from app.services.monday_sync_service import MondaySyncService

                counts = MondaySyncService(self.db).sync_user(user, reason="n8n")
                return _ok("monday", "sync", counts)
            if key == "clickup":
                from app.services.clickup_sync_service import ClickUpSyncService

                counts = ClickUpSyncService(self.db).sync_user(user, reason="n8n")
                return _ok("clickup", "sync", counts)
            return {
                "provider": key,
                "action": "sync",
                "status": "skipped",
                "detail": "Unknown provider",
            }
        except HTTPException as exc:
            # Not connected / missing scope → skip, not hard-fail the workflow.
            if exc.status_code in (
                status.HTTP_404_NOT_FOUND,
                status.HTTP_409_CONFLICT,
            ):
                return {
                    "provider": key,
                    "action": "sync",
                    "status": "skipped",
                    "detail": str(exc.detail),
                }
            logger.warning("Provider sync error %s: %s", key, exc.detail)
            return {
                "provider": key,
                "action": "sync",
                "status": "error",
                "detail": str(exc.detail),
            }
        except Exception as exc:
            logger.warning("Provider sync failed %s", key, exc_info=True)
            return {
                "provider": key,
                "action": "sync",
                "status": "error",
                "detail": str(exc),
            }

    def _regenerate_morning_brief(self, user: User) -> dict[str, Any]:
        try:
            from app.services.morning_brief_service import MorningBriefService

            brief = MorningBriefService(self.db, user).regenerate()
            return {
                "provider": "morning-brief",
                "action": "regenerate",
                "status": "success",
                "detail": brief.meta.headline if hasattr(brief, "meta") else "regenerated",
            }
        except Exception as exc:
            logger.warning("Morning brief regenerate failed", exc_info=True)
            return {
                "provider": "morning-brief",
                "action": "regenerate",
                "status": "error",
                "detail": str(exc),
            }

    def _regenerate_weekly_digest(self, user: User) -> dict[str, Any]:
        try:
            from app.services.weekly_digest_service import WeeklyDigestService

            digest = WeeklyDigestService(self.db, user).regenerate()
            return {
                "provider": "weekly-digest",
                "action": "regenerate",
                "status": "success",
                "detail": digest.headline,
            }
        except Exception as exc:
            logger.warning("Weekly digest regenerate failed", exc_info=True)
            return {
                "provider": "weekly-digest",
                "action": "regenerate",
                "status": "error",
                "detail": str(exc),
            }


def _ok(provider: str, action: str, counts: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "provider": provider,
        "action": action,
        "status": "success",
        "detail": counts or {},
    }
