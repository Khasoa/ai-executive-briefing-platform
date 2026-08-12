"""Notion OAuth2 Authorization Code provider.

Notion returns a long-lived workspace bot token (typically no refresh token).
Capabilities are chosen by the user when installing the integration.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_ME_URL = "https://api.notion.com/v1/users/me"
NOTION_VERSION = "2022-06-28"

# Capability labels stored on Integration.scopes (Notion OAuth has no Google-style list).
NOTION_CAPABILITY_SCOPES = (
    "read_content",
    "read_user",
)


class NotionOAuthProvider(OAuthProvider):
    name = "notion"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client_id = settings.notion_client_id.strip()
        self.client_secret = settings.notion_client_secret.strip()
        self.redirect_uri = settings.notion_redirect_uri.strip()
        self._timeout = settings.oauth_http_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def default_scopes(self) -> list[str]:
        return list(NOTION_CAPABILITY_SCOPES)

    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        self._require_configured()
        # Notion does not take a scope query param — capabilities are set in the integration.
        _ = scopes
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{NOTION_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokenSet:
        self._require_configured()
        data = self._token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri})
        return self._to_token_set(data)

    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        # Notion bot tokens are long-lived; refresh is not supported.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notion access tokens cannot be refreshed — reconnect the workspace",
        )

    def fetch_profile(self, access_token: str) -> OAuthProfile:
        self._require_configured()
        try:
            response = httpx.get(
                NOTION_ME_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": NOTION_VERSION,
                    "Accept": "application/json",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch Notion bot profile",
            ) from exc

        raw = response.json()
        bot = raw.get("bot") or {}
        owner = bot.get("owner") or raw.get("owner") or {}
        user = owner.get("user") or {}
        person = user.get("person") or {}

        subject = str(user.get("id") or raw.get("id") or "")
        email = (person.get("email") or "").strip().lower()
        name = (user.get("name") or raw.get("name") or "Notion workspace").strip()
        if not email:
            # Workspace installs may not expose a person email — synthesise a stable handle.
            workspace = (bot.get("workspace_name") or "workspace").strip().lower().replace(" ", "-")
            email = f"notion+{subject or workspace}@users.notion.local"

        if not subject:
            subject = email

        return OAuthProfile(
            subject=subject,
            email=email,
            email_verified=bool(person.get("email")),
            full_name=name[:255],
            given_name=(name.split()[0] if name else None),
            picture_url=(user.get("avatar_url") or None),
            raw={
                **raw,
                "workspace_id": bot.get("workspace_id") or raw.get("workspace_id"),
                "workspace_name": bot.get("workspace_name") or raw.get("workspace_name"),
            },
        )

    def _token_request(self, form: dict[str, str]) -> dict:
        credentials = f"{self.client_id}:{self.client_secret}".encode()
        basic = base64.b64encode(credentials).decode()
        try:
            response = httpx.post(
                NOTION_TOKEN_URL,
                json=form,
                headers={
                    "Authorization": f"Basic {basic}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach Notion token endpoint",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notion rejected the OAuth token request",
            )
        return response.json()

    def _to_token_set(self, data: dict) -> OAuthTokenSet:
        access = data.get("access_token")
        if not access:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Notion token response missing access_token",
            )
        # Long-lived — no expires_in from Notion.
        return OAuthTokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=None,
            token_type=data.get("token_type") or "bearer",
            scope=data.get("workspace_id") or data.get("workspace_name"),
            id_token=None,
            raw=data,
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Notion OAuth is not configured",
            )
