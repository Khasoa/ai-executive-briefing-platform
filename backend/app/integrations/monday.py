"""monday.com GraphQL API client (read-only boards/items)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_VERSION = "2024-10"


class MondayError(Exception):
    pass


class MondayUnauthorized(MondayError):
    pass


class MondayRateLimit(MondayError):
    pass


class MondayClient:
    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or get_settings()
        self._timeout = self.settings.oauth_http_timeout_seconds

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = httpx.post(
                MONDAY_API_URL,
                json={"query": query, "variables": variables or {}},
                headers={
                    "Authorization": self.access_token,
                    "Content-Type": "application/json",
                    "API-Version": MONDAY_API_VERSION,
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise MondayError(f"monday.com request failed: {exc}") from exc

        if response.status_code == 401:
            raise MondayUnauthorized("monday.com authorization expired")
        if response.status_code == 429:
            raise MondayRateLimit("monday.com rate limit exceeded")
        if response.status_code >= 400:
            raise MondayError(f"monday.com HTTP {response.status_code}")

        payload = response.json()
        errors = payload.get("errors") or []
        if errors:
            message = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
            lowered = (message or "").lower()
            if "auth" in lowered or "unauthorized" in lowered:
                raise MondayUnauthorized(message or "unauthorized")
            raise MondayError(message or "monday.com GraphQL error")
        return payload.get("data") or {}

    def list_boards(self, *, limit: int = 50) -> list[dict[str, Any]]:
        query = """
        query ($limit: Int!) {
          boards(limit: $limit, order_by: created_at) {
            id
            name
            state
            workspace_id
            url
          }
        }
        """
        data = self.graphql(query, {"limit": limit})
        boards = data.get("boards") or []
        return [b for b in boards if isinstance(b, dict) and b.get("state") != "deleted"]

    def list_board_items(
        self,
        board_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if cursor:
            query = """
            query ($cursor: String!, $limit: Int!) {
              next_items_page(cursor: $cursor, limit: $limit) {
                cursor
                items {
                  id
                  name
                  state
                  updated_at
                  url
                  group { id title }
                  column_values { id type text value }
                }
              }
            }
            """
            data = self.graphql(query, {"cursor": cursor, "limit": limit})
            page = data.get("next_items_page") or {}
        else:
            query = """
            query ($boardId: ID!, $limit: Int!) {
              boards(ids: [$boardId]) {
                id
                name
                workspace_id
                items_page(limit: $limit) {
                  cursor
                  items {
                    id
                    name
                    state
                    updated_at
                    url
                    group { id title }
                    column_values { id type text value }
                  }
                }
              }
            }
            """
            data = self.graphql(query, {"boardId": board_id, "limit": limit})
            boards = data.get("boards") or []
            if not boards:
                return {"cursor": None, "items": [], "board": {}}
            board = boards[0]
            page = board.get("items_page") or {}
            page = {**page, "board": board}
        return {
            "cursor": page.get("cursor"),
            "items": page.get("items") or [],
            "board": page.get("board") or {},
        }
