"""ClickUp OAuth2 Authorization Code provider.

Auth: https://app.clickup.com/api
Token: POST https://api.clickup.com/api/v2/oauth/token
Access tokens currently do not expire; users select Workspaces at consent (no scopes).
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet

CLICKUP_AUTH_URL = "https://app.clickup.com/api"
CLICKUP_TOKEN_URL = "https://api.clickup.com/api/v2/oauth/token"
CLICKUP_USER_URL = "https://api.clickup.com/api/v2/user"
CLICKUP_TEAMS_URL = "https://api.clickup.com/api/v2/team"

# ClickUp OAuth has no granular scopes — labels for Integration.scopes display.
CLICKUP_CAPABILITY_SCOPES = ("workspace.read", "tasks.read")


class ClickUpOAuthProvider(OAuthProvider):
    name = "clickup"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client_id = settings.clickup_client_id.strip()
        self.client_secret = settings.clickup_client_secret.strip()
        self.redirect_uri = settings.clickup_redirect_uri.strip()
        self._timeout = settings.oauth_http_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def default_scopes(self) -> list[str]:
        return list(CLICKUP_CAPABILITY_SCOPES)

    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        self._require_configured()
        _ = scopes
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{CLICKUP_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokenSet:
        self._require_configured()
        try:
            response = httpx.post(
                CLICKUP_TOKEN_URL,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach ClickUp token endpoint",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ClickUp rejected the OAuth token request",
            )
        data = response.json()
        access = data.get("access_token")
        if not access:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="ClickUp token response missing access_token",
            )
        return OAuthTokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=None,
            token_type=data.get("token_type") or "bearer",
            scope=None,
            id_token=None,
            raw=data,
        )

    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ClickUp access tokens cannot be refreshed — reconnect the workspace",
        )

    def fetch_profile(self, access_token: str) -> OAuthProfile:
        self._require_configured()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            user_resp = httpx.get(CLICKUP_USER_URL, headers=headers, timeout=self._timeout)
            user_resp.raise_for_status()
            teams_resp = httpx.get(CLICKUP_TEAMS_URL, headers=headers, timeout=self._timeout)
            teams_resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch ClickUp profile",
            ) from exc

        user = (user_resp.json() or {}).get("user") or {}
        teams = (teams_resp.json() or {}).get("teams") or []
        subject = str(user.get("id") or "")
        email = (user.get("email") or "").strip().lower()
        name = (user.get("username") or user.get("email") or "ClickUp").strip()
        if not email:
            email = f"clickup+{subject or 'user'}@users.clickup.local"
        if not subject:
            subject = email

        primary = teams[0] if teams else {}
        return OAuthProfile(
            subject=subject,
            email=email,
            email_verified=bool(user.get("email")),
            full_name=name[:255],
            given_name=(name.split()[0] if name else None),
            picture_url=user.get("profilePicture"),
            raw={
                "user": user,
                "teams": teams,
                "workspace_id": str(primary.get("id") or ""),
                "workspace_name": primary.get("name") or "",
            },
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ClickUp OAuth is not configured",
            )
