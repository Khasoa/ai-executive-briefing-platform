"""Notion API client — search, databases, pages. No business logic."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("briefly.notion")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionError(Exception):
    pass


class NotionUnauthorized(NotionError):
    pass


class NotionRateLimit(NotionError):
    pass


class NotionUnavailable(NotionError):
    pass


class NotionClient:
    """Thin Notion REST wrapper used only by NotionSyncService."""

    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self.timeout = float(self.settings.oauth_http_timeout_seconds)

    def search(
        self,
        *,
        query: str | None = None,
        filter_object: str | None = None,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "page_size": min(page_size, 100),
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        }
        if query:
            body["query"] = query
        if filter_object in ("page", "database"):
            body["filter"] = {"value": filter_object, "property": "object"}
        if start_cursor:
            body["start_cursor"] = start_cursor
        return self._post("/search", body)

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self._get(f"/pages/{page_id}")

    def get_database(self, database_id: str) -> dict[str, Any]:
        return self._get(f"/databases/{database_id}")

    def query_database(
        self,
        database_id: str,
        *,
        start_cursor: str | None = None,
        page_size: int = 100,
        filter_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "page_size": min(page_size, 100),
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        }
        if start_cursor:
            body["start_cursor"] = start_cursor
        if filter_body:
            body["filter"] = filter_body
        return self._post(f"/databases/{database_id}/query", body)

    def list_block_children(self, block_id: str, *, page_size: int = 20) -> dict[str, Any]:
        return self._get(f"/blocks/{block_id}/children", params={"page_size": str(page_size)})

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": NOTION_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json_body=body)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise NotionUnavailable("Notion request timed out") from exc
        except httpx.HTTPError as exc:
            raise NotionUnavailable("Notion provider unreachable") from exc

        if response.status_code == 401:
            raise NotionUnauthorized("Notion authentication failed")
        if response.status_code == 429:
            raise NotionRateLimit("Notion rate limit exceeded")
        if response.status_code >= 500:
            raise NotionUnavailable(f"Notion unavailable ({response.status_code})")
        if response.status_code >= 400:
            raise NotionError(f"Notion rejected the request ({response.status_code})")

        try:
            return response.json()
        except ValueError as exc:
            raise NotionError("Notion returned non-JSON body") from exc
