"""ClickUp REST API v2 client (read-only workspaces/tasks)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"


class ClickUpError(Exception):
    pass


class ClickUpUnauthorized(ClickUpError):
    pass


class ClickUpRateLimit(ClickUpError):
    pass


class ClickUpClient:
    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self._timeout = self.settings.oauth_http_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{CLICKUP_API_BASE}{path}",
                headers=self._headers(),
                params=params or {},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClickUpError(f"ClickUp request failed: {exc}") from exc

        if response.status_code == 401:
            raise ClickUpUnauthorized("ClickUp authorization expired")
        if response.status_code == 429:
            raise ClickUpRateLimit("ClickUp rate limit exceeded")
        if response.status_code >= 400:
            raise ClickUpError(f"ClickUp HTTP {response.status_code}: {response.text[:200]}")
        return response.json()

    def list_teams(self) -> list[dict[str, Any]]:
        data = self._get("/team")
        return [t for t in (data.get("teams") or []) if isinstance(t, dict)]

    def list_team_tasks(
        self,
        team_id: str,
        *,
        page: int = 0,
        include_closed: bool = True,
        date_updated_gt: int | None = None,
        subtasks: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "include_closed": str(include_closed).lower(),
            "subtasks": str(subtasks).lower(),
        }
        if date_updated_gt is not None:
            params["date_updated_gt"] = date_updated_gt
        return self._get(f"/team/{team_id}/task", params=params)
