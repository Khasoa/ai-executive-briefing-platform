"""GoHighLevel REST client — opportunities + pipelines. No business logic."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("briefly.ghl")

GHL_API_BASE = "https://services.leadconnectorhq.com"
GHL_VERSION = "2021-07-28"


class GHLError(Exception):
    pass


class GHLUnauthorized(GHLError):
    pass


class GHLRateLimit(GHLError):
    pass


class GHLUnavailable(GHLError):
    pass


class GHLClient:
    """Thin LeadConnector REST wrapper used only by GHLSyncService."""

    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self.timeout = float(self.settings.oauth_http_timeout_seconds)

    def list_pipelines(self, location_id: str) -> list[dict[str, Any]]:
        payload = self._get(
            "/opportunities/pipelines",
            params={"locationId": location_id},
        )
        return list(payload.get("pipelines") or [])

    def search_opportunities(
        self,
        *,
        location_id: str,
        status: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "location_id": location_id,
            "limit": str(min(limit, 100)),
            "skip": str(max(skip, 0)),
        }
        if status:
            params["status"] = status
        return self._get("/opportunities/search", params=params)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Version": GHL_VERSION,
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{GHL_API_BASE}{path}"
        try:
            response = httpx.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise GHLUnavailable("GoHighLevel request timed out") from exc
        except httpx.HTTPError as exc:
            raise GHLUnavailable("GoHighLevel provider unreachable") from exc

        if response.status_code == 401:
            raise GHLUnauthorized("GoHighLevel authentication failed")
        if response.status_code == 429:
            raise GHLRateLimit("GoHighLevel rate limit exceeded")
        if response.status_code >= 500:
            raise GHLUnavailable(f"GoHighLevel unavailable ({response.status_code})")
        if response.status_code >= 400:
            raise GHLError(f"GoHighLevel rejected the request ({response.status_code})")

        try:
            return response.json()
        except ValueError as exc:
            raise GHLError("GoHighLevel returned non-JSON body") from exc
