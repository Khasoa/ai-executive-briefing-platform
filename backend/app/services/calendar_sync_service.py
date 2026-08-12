"""Synchronize Google Calendar events into `Meeting` rows.

MeetingService stays read-only: when synced rows exist for the user they
surface automatically via `list_meetings()`; otherwise demo fallback remains.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.google_calendar import (
    CALENDAR_READONLY_SCOPE,
    PRIMARY_CALENDAR,
    GoogleCalendarClient,
    GoogleCalendarSyncTokenExpired,
)
from app.models import Integration, Meeting, SyncEvent, User
from app.services.agenda_sanitize import detect_recurring, sanitize_agenda
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.calendar_sync")

GOOGLE_PROVIDER = "google"
GOOGLE_CALENDAR_PROVIDER = "google-calendar"
SOURCE = "Google Calendar"


class CalendarSyncService:
    """Incremental, idempotent Calendar → Meeting sync (webhook-ready)."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        """Pull changes for `user` and upsert/delete Meeting rows.

        Returns counts: ``{"upserted": n, "deleted": n, "pages": n}``.
        """
        google = self._require_google_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, GOOGLE_PROVIDER)
        self._ensure_calendar_scope(google)

        client = GoogleCalendarClient(access_token, self.settings)
        calendar_meta = dict((google.config or {}).get("calendar") or {})
        sync_token = calendar_meta.get("sync_token")

        try:
            counts = self._sync_pages(user, client, sync_token=sync_token)
        except GoogleCalendarSyncTokenExpired:
            logger.info("Google syncToken expired for user %s — full resync", user.id)
            calendar_meta.pop("sync_token", None)
            self._save_calendar_meta(google, calendar_meta)
            counts = self._sync_pages(user, client, sync_token=None)

        # Refresh google row (config may have changed) and mirror UI integration.
        self.db.refresh(google)
        calendar_meta = dict((google.config or {}).get("calendar") or {})
        self._ensure_calendar_integration_row(user, google, calendar_meta, reason)
        return counts

    def handle_webhook(
        self,
        *,
        channel_id: str,
        resource_state: str | None,
        resource_id: str | None = None,
    ) -> dict[str, int] | None:
        """Process a Google push notification. Returns sync counts or None if ignored."""
        if resource_state in (None, "sync"):  # initial handshake — acknowledge only
            return None

        integration = self._find_by_channel(channel_id)
        if integration is None:
            logger.warning("No integration for Google Calendar channel %s", channel_id)
            return None

        if resource_id and (integration.config or {}).get("calendar", {}).get("resource_id"):
            stored = integration.config["calendar"].get("resource_id")
            if stored and stored != resource_id:
                logger.warning("Google Calendar webhook resource_id mismatch")
                return None

        user = self.db.get(User, integration.user_id)
        if user is None or not user.is_active:
            return None
        return self.sync_user(user, reason="webhook")

    def ensure_watch(self, user: User) -> dict[str, Any] | None:
        """Register (or refresh) a Calendar push channel when webhook URL is configured."""
        webhook_url = self.settings.google_calendar_webhook_url.strip()
        if not webhook_url:
            return None

        google = self._require_google_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, GOOGLE_PROVIDER)
        client = GoogleCalendarClient(access_token, self.settings)
        calendar_meta = dict((google.config or {}).get("calendar") or {})

        channel_id = calendar_meta.get("channel_id") or f"briefly-{user.id}-{secrets.token_hex(8)}"
        channel = client.register_watch(
            channel_id=channel_id,
            webhook_url=webhook_url,
            token=str(user.id),
        )
        calendar_meta.update(
            {
                "channel_id": channel.channel_id,
                "resource_id": channel.resource_id,
                "channel_expiration_ms": channel.expiration_ms,
                "calendar_id": PRIMARY_CALENDAR,
            }
        )
        self._save_calendar_meta(google, calendar_meta)
        return calendar_meta

    def _sync_pages(
        self,
        user: User,
        client: GoogleCalendarClient,
        *,
        sync_token: str | None,
    ) -> dict[str, int]:
        upserted = deleted = pages = 0
        page_token = None
        next_sync_token = None
        time_min = time_max = None
        if not sync_token:
            now = datetime.now(timezone.utc)
            time_min = now - timedelta(days=self.settings.google_calendar_sync_lookback_days)
            time_max = now + timedelta(days=self.settings.google_calendar_sync_lookahead_days)

        while True:
            page = client.list_event_changes(
                sync_token=sync_token,
                page_token=page_token,
                time_min=time_min,
                time_max=time_max,
            )
            pages += 1
            for event in page.events:
                if self._apply_event(user, event):
                    if (event.get("status") or "").lower() == "cancelled":
                        deleted += 1
                    else:
                        upserted += 1
            if page.next_sync_token:
                next_sync_token = page.next_sync_token
            page_token = page.next_page_token
            if not page_token:
                break
            # After first page of incremental sync, only pageToken is used
            # (syncToken cannot be combined with pageToken on subsequent pages).
            sync_token = None
            time_min = time_max = None

        google = self._require_google_integration(user)
        calendar_meta = dict((google.config or {}).get("calendar") or {})
        if next_sync_token:
            calendar_meta["sync_token"] = next_sync_token
        calendar_meta["calendar_id"] = PRIMARY_CALENDAR
        calendar_meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        self._save_calendar_meta(google, calendar_meta)
        self.db.commit()
        return {"upserted": upserted, "deleted": deleted, "pages": pages}

    def _apply_event(self, user: User, event: dict[str, Any]) -> bool:
        event_id = event.get("id")
        if not event_id:
            return False

        external_id = f"{PRIMARY_CALENDAR}:{event_id}"
        existing = (
            self.db.query(Meeting)
            .filter(Meeting.user_id == user.id, Meeting.external_id == external_id)
            .first()
        )

        if (event.get("status") or "").lower() == "cancelled":
            if existing is not None:
                self.db.delete(existing)
                self.db.flush()
                return True
            return False

        starts_at, ends_at, all_day = _parse_event_bounds(event)
        if starts_at is None or ends_at is None:
            return False

        mapped = {
            "title": (event.get("summary") or "(No title)").strip()[:500],
            "starts_at": starts_at,
            "ends_at": ends_at,
            "location": _location(event),
            "attendees": _attendees(event),
            "type": _meeting_type(event),
            "sources": [SOURCE],
        }

        if existing is None:
            meeting = Meeting(
                user_id=user.id,
                external_id=external_id,
                prep_status="needs-prep",
                prep_reason="Imported from Google Calendar — preparation not generated yet.",
                agenda=_agenda_from_description(event),
                company=_default_company(event),
                intelligence={
                    "relatedEmails": [],
                    "preparationNotes": [],
                    "talkingPoints": [],
                    "recommendedQuestions": [],
                    "risks": [],
                    "google": _google_intelligence_meta(event, all_day=all_day),
                },
                **mapped,
            )
            self.db.add(meeting)
        else:
            for field, value in mapped.items():
                setattr(existing, field, value)
            # Preserve local Briefly metadata; refresh sanitized agenda when empty or dump-like.
            from app.services.agenda_sanitize import looks_like_recurring_series_dump

            existing_agenda_text = "\n".join(existing.agenda or [])
            if not existing.agenda or looks_like_recurring_series_dump(existing_agenda_text):
                existing.agenda = _agenda_from_description(event)
            if not existing.company or not existing.company.get("name"):
                existing.company = _default_company(event)
            intelligence = dict(existing.intelligence or {})
            google_meta = dict(intelligence.get("google") or {})
            google_meta.update(_google_intelligence_meta(event, all_day=all_day))
            intelligence["google"] = google_meta
            for key in (
                "relatedEmails",
                "preparationNotes",
                "talkingPoints",
                "recommendedQuestions",
                "risks",
            ):
                intelligence.setdefault(key, [])
            existing.intelligence = intelligence
            # Explicitly keep prep_* as-is (no assignment).

        self.db.flush()
        return True

    def _require_google_integration(self, user: User) -> Integration:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == GOOGLE_PROVIDER,
                Integration.status == "connected",
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google is not connected for this user",
            )
        return row

    def _ensure_calendar_scope(self, google: Integration) -> None:
        scopes = " ".join(google.scopes or [])
        oauth_scope = ((google.config or {}).get("oauth") or {}).get("scope") or ""
        combined = f"{scopes} {oauth_scope}"
        if CALENDAR_READONLY_SCOPE not in combined and "calendar.readonly" not in combined:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Google Calendar permission missing — reconnect Google to grant "
                    "calendar.readonly"
                ),
            )

    def _save_calendar_meta(self, google: Integration, calendar_meta: dict[str, Any]) -> None:
        config = dict(google.config or {})
        config["calendar"] = calendar_meta
        google.config = config
        google.last_sync_at = datetime.now(timezone.utc)
        google.status = "connected"
        self.db.add(google)
        self.db.commit()

    def _ensure_calendar_integration_row(
        self,
        user: User,
        google: Integration,
        calendar_meta: dict[str, Any],
        reason: str,
    ) -> None:
        """Keep a `google-calendar` Integration row for the Integrations UI / sync audit."""
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == GOOGLE_CALENDAR_PROVIDER,
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        display = {
            "name": "Google Calendar",
            "category": "Calendar",
            "description": "Meetings, attendees and scheduling context for meeting intelligence.",
            "poweredBy": "Google Calendar API",
            "metrics": [],
            "calendar": calendar_meta,
            "token_provider": GOOGLE_PROVIDER,
        }
        display.pop("last_error", None)
        if row is None:
            row = Integration(
                user_id=user.id,
                provider=GOOGLE_CALENDAR_PROVIDER,
                status="connected",
                account=google.account,
                scopes=[CALENDAR_READONLY_SCOPE],
                config=display,
                connected_at=now,
                last_sync_at=now,
            )
            self.db.add(row)
        else:
            prior = dict(row.config or {})
            prior.pop("last_error", None)
            display = {**prior, **display}
            display.pop("last_error", None)
            row.status = "connected"
            row.account = google.account
            row.scopes = [CALENDAR_READONLY_SCOPE]
            row.config = display
            row.last_sync_at = now
            row.connected_at = row.connected_at or now

        self.db.flush()
        self.db.add(
            SyncEvent(
                integration_id=row.id,
                event="Calendar sync completed" if reason != "webhook" else "Calendar webhook sync",
                status="success",
                detail=f"reason={reason}",
                occurred_at=now,
            )
        )
        self.db.commit()

    def _find_by_channel(self, channel_id: str) -> Integration | None:
        # Prefer google-calendar row, then google identity row.
        for provider in (GOOGLE_CALENDAR_PROVIDER, GOOGLE_PROVIDER):
            rows = (
                self.db.query(Integration)
                .filter(Integration.provider == provider, Integration.status == "connected")
                .all()
            )
            for row in rows:
                calendar = (row.config or {}).get("calendar") or {}
                if calendar.get("channel_id") == channel_id:
                    return row
        return None


def _parse_event_bounds(event: dict[str, Any]) -> tuple[datetime | None, datetime | None, bool]:
    start = event.get("start") or {}
    end = event.get("end") or {}
    if start.get("dateTime") and end.get("dateTime"):
        return _parse_dt(start["dateTime"]), _parse_dt(end["dateTime"]), False
    if start.get("date") and end.get("date"):
        # All-day: end is exclusive per Google.
        start_dt = datetime.fromisoformat(start["date"]).replace(tzinfo=timezone.utc)
        end_exclusive = datetime.fromisoformat(end["date"]).replace(tzinfo=timezone.utc)
        end_dt = end_exclusive - timedelta(seconds=1)
        return start_dt, end_dt, True
    return None, None, False


def _parse_dt(value: str) -> datetime:
    normalised = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalised)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _location(event: dict[str, Any]) -> str:
    location = (event.get("location") or "").strip()
    if location:
        return location[:255]
    conf = event.get("conferenceData") or {}
    for ep in conf.get("entryPoints") or []:
        if ep.get("entryPointType") == "video" and ep.get("uri"):
            return str(ep["uri"])[:255]
    return "Google Calendar"


def _attendees(event: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for attendee in event.get("attendees") or []:
        email = (attendee.get("email") or "").strip()
        name = (attendee.get("displayName") or email or "Guest").strip()
        initials = "".join(part[0] for part in name.split()[:2]).upper() or "G"
        result.append(
            {
                "name": name[:100],
                "role": "Organizer" if attendee.get("organizer") else "Attendee",
                "company": "",
                "avatar": initials[:10],
            }
        )
    return result


def _agenda_from_description(event: dict[str, Any]) -> list[str]:
    description = event.get("description") or ""
    return sanitize_agenda([], description=description, max_items=8)


def _default_company(event: dict[str, Any]) -> dict[str, str]:
    organizer = (event.get("organizer") or {}).get("displayName") or (
        (event.get("organizer") or {}).get("email") or "Google Calendar"
    )
    return {
        "name": str(organizer)[:255],
        "industry": "",
        "size": "",
        "relationship": "Calendar event",
        "background": (event.get("summary") or "")[:500],
    }


def _meeting_type(event: dict[str, Any]) -> str:
    text = f"{event.get('summary') or ''} {event.get('description') or ''}".lower()
    if any(word in text for word in ("board", "investor", "series", "fund")):
        return "investor"
    if any(word in text for word in ("client", "customer", "renewal", "demo")):
        return "client"
    if any(word in text for word in ("personal", "dentist", "doctor", "family")):
        return "personal"
    return "internal"


def _google_intelligence_meta(event: dict[str, Any], *, all_day: bool) -> dict[str, Any]:
    return {
        "eventId": event.get("id"),
        "calendarId": PRIMARY_CALENDAR,
        "htmlLink": event.get("htmlLink"),
        "allDay": all_day,
        "updated": event.get("updated"),
        "recurringEventId": event.get("recurringEventId"),
        "recurrence": event.get("recurrence"),
        "isRecurring": detect_recurring(event),
    }
