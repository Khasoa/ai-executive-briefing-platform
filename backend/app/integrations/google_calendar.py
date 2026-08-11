"""Google Calendar API client — read-only events + watch registration.

Does not own persistence. Callers (`CalendarSyncService`) apply changes to
`Meeting` rows. Tokens come from `OAuthService` (provider=`google`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
PRIMARY_CALENDAR = "primary"


@dataclass
class CalendarEventPage:
    events: list[dict[str, Any]] = field(default_factory=list)
    next_page_token: str | None = None
    next_sync_token: str | None = None


@dataclass
class CalendarWatchChannel:
    channel_id: str
    resource_id: str
    expiration_ms: int | None
    resource_uri: str | None = None


class GoogleCalendarClient:
    """Thin Calendar v3 wrapper. Webhook registration is supported for later ops."""

    def __init__(
        self,
        access_token: str,
        settings: Settings | None = None,
        *,
        calendar_id: str = PRIMARY_CALENDAR,
    ) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self.calendar_id = calendar_id
        self._timeout = self.settings.oauth_http_timeout_seconds

    def list_event_changes(
        self,
        *,
        sync_token: str | None = None,
        page_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> CalendarEventPage:
        """Incremental sync when `sync_token` is set; otherwise a windowed full pull."""
        params: dict[str, str] = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": "250",
        }
        if page_token:
            params["pageToken"] = page_token
        if sync_token:
            params["syncToken"] = sync_token
        else:
            if time_min is not None:
                params["timeMin"] = _rfc3339(time_min)
            if time_max is not None:
                params["timeMax"] = _rfc3339(time_max)
            params["orderBy"] = "startTime"

        url = f"{CALENDAR_API}/calendars/{self.calendar_id}/events?{urlencode(params)}"
        data = self._get_json(url)
        return CalendarEventPage(
            events=list(data.get("items") or []),
            next_page_token=data.get("nextPageToken"),
            next_sync_token=data.get("nextSyncToken"),
        )

    def register_watch(
        self,
        *,
        channel_id: str,
        webhook_url: str,
        token: str | None = None,
        ttl_seconds: int = 86400,
    ) -> CalendarWatchChannel:
        """Register a push notification channel (webhook-ready; optional in Phase 2.3)."""
        body: dict[str, Any] = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
            "params": {"ttl": str(ttl_seconds)},
        }
        if token:
            body["token"] = token

        url = f"{CALENDAR_API}/calendars/{self.calendar_id}/events/watch"
        data = self._request_json("POST", url, json_body=body)
        return CalendarWatchChannel(
            channel_id=str(data.get("id") or channel_id),
            resource_id=str(data.get("resourceId") or ""),
            expiration_ms=int(data["expiration"]) if data.get("expiration") else None,
            resource_uri=data.get("resourceUri"),
        )

    def stop_watch(self, *, channel_id: str, resource_id: str) -> None:
        url = f"{CALENDAR_API}/channels/stop"
        self._request_json(
            "POST",
            url,
            json_body={"id": channel_id, "resourceId": resource_id},
            allow_empty=True,
        )

    def _get_json(self, url: str) -> dict[str, Any]:
        return self._request_json("GET", url)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach Google Calendar",
            ) from exc

        if response.status_code < 400:
            if allow_empty and not response.content:
                return {}
            return response.json()

        from app.integrations.google_api_errors import raise_for_google_response

        raise_for_google_response(
            response,
            product="Google Calendar",
            sync_token_expired_exc=GoogleCalendarSyncTokenExpired,
        )
        return {}  # pragma: no cover


class GoogleCalendarSyncTokenExpired(Exception):
    """Raised when Google returns HTTP 410 for an incremental syncToken."""


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
