"""Gmail API client — read-only messages + history + watch.

Does not own persistence. Callers (`GmailSyncService`) apply changes to
`Email` rows. Tokens come from `OAuthService` (provider=`google`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


@dataclass
class GmailListPage:
    message_refs: list[dict[str, str]] = field(default_factory=list)
    next_page_token: str | None = None
    result_size_estimate: int | None = None


@dataclass
class GmailHistoryPage:
    messages_added: list[str] = field(default_factory=list)
    messages_deleted: list[str] = field(default_factory=list)
    labels_changed: list[str] = field(default_factory=list)
    next_page_token: str | None = None
    history_id: str | None = None


@dataclass
class GmailWatchResult:
    history_id: str
    expiration_ms: int | None


class GmailHistoryExpired(Exception):
    """Raised when Gmail returns HTTP 404 for a stale startHistoryId."""


class GmailClient:
    """Thin Gmail v1 wrapper. Push watch is supported for later ops."""

    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self._timeout = self.settings.oauth_http_timeout_seconds

    def get_profile(self) -> dict[str, Any]:
        return self._get_json(f"{GMAIL_API}/users/me/profile")

    def list_messages(
        self,
        *,
        query: str | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> GmailListPage:
        params: dict[str, str] = {"maxResults": str(max_results)}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token
        url = f"{GMAIL_API}/users/me/messages?{urlencode(params)}"
        data = self._get_json(url)
        refs = [
            {"id": str(item["id"]), "threadId": str(item.get("threadId") or "")}
            for item in (data.get("messages") or [])
            if item.get("id")
        ]
        return GmailListPage(
            message_refs=refs,
            next_page_token=data.get("nextPageToken"),
            result_size_estimate=data.get("resultSizeEstimate"),
        )

    def get_message(self, message_id: str, *, format: str = "metadata") -> dict[str, Any]:
        query = urlencode(
            [
                ("format", format),
                ("metadataHeaders", "From"),
                ("metadataHeaders", "To"),
                ("metadataHeaders", "Subject"),
                ("metadataHeaders", "Date"),
            ]
        )
        return self._get_json(f"{GMAIL_API}/users/me/messages/{message_id}?{query}")

    def list_history(
        self,
        *,
        start_history_id: str,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> GmailHistoryPage:
        query_items: list[tuple[str, str]] = [
            ("startHistoryId", start_history_id),
            ("maxResults", str(max_results)),
            ("historyTypes", "messageAdded"),
            ("historyTypes", "messageDeleted"),
            ("historyTypes", "labelAdded"),
            ("historyTypes", "labelRemoved"),
        ]
        if page_token:
            query_items.append(("pageToken", page_token))
        url = f"{GMAIL_API}/users/me/history?{urlencode(query_items)}"
        try:
            data = self._get_json(url)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise GmailHistoryExpired() from exc
            raise

        added: list[str] = []
        deleted: list[str] = []
        labeled: list[str] = []
        for entry in data.get("history") or []:
            for item in entry.get("messagesAdded") or []:
                msg = item.get("message") or {}
                if msg.get("id"):
                    added.append(str(msg["id"]))
            for item in entry.get("messagesDeleted") or []:
                msg = item.get("message") or {}
                if msg.get("id"):
                    deleted.append(str(msg["id"]))
            for item in entry.get("labelsAdded") or []:
                msg = item.get("message") or {}
                if msg.get("id"):
                    labeled.append(str(msg["id"]))
            for item in entry.get("labelsRemoved") or []:
                msg = item.get("message") or {}
                if msg.get("id"):
                    labeled.append(str(msg["id"]))

        return GmailHistoryPage(
            messages_added=added,
            messages_deleted=deleted,
            labels_changed=labeled,
            next_page_token=data.get("nextPageToken"),
            history_id=str(data["historyId"]) if data.get("historyId") is not None else None,
        )

    def list_labels(self) -> dict[str, str]:
        """Return map of labelId → label name."""
        data = self._get_json(f"{GMAIL_API}/users/me/labels")
        return {
            str(label["id"]): str(label.get("name") or label["id"])
            for label in (data.get("labels") or [])
            if label.get("id")
        }

    def register_watch(self, *, topic_name: str, label_ids: list[str] | None = None) -> GmailWatchResult:
        """Register a Pub/Sub watch (webhook-ready; requires GCP topic)."""
        body: dict[str, Any] = {"topicName": topic_name}
        if label_ids:
            body["labelIds"] = label_ids
        data = self._request_json("POST", f"{GMAIL_API}/users/me/watch", json_body=body)
        return GmailWatchResult(
            history_id=str(data.get("historyId") or ""),
            expiration_ms=int(data["expiration"]) if data.get("expiration") else None,
        )

    def stop_watch(self) -> None:
        self._request_json("POST", f"{GMAIL_API}/users/me/stop", json_body={}, allow_empty=True)

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
                detail="Failed to reach Gmail",
            ) from exc

        if response.status_code < 400:
            if allow_empty and not response.content:
                return {}
            return response.json()

        from app.integrations.google_api_errors import raise_for_google_response

        raise_for_google_response(response, product="Gmail")
        return {}  # pragma: no cover
