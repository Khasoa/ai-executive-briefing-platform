"""monday.com OAuth2 Authorization Code provider (documented legacy flow).

Auth: https://auth.monday.com/oauth2/authorize
Token: https://auth.monday.com/oauth2/token
Access tokens do not expire until the app is uninstalled (no refresh token).
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet

MONDAY_AUTH_URL = "https://auth.monday.com/oauth2/authorize"
MONDAY_TOKEN_URL = "https://auth.monday.com/oauth2/token"
MONDAY_API_URL = "https://api.monday.com/v2"

MONDAY_SCOPES = (
    "me:read",
    "boards:read",
    "workspaces:read",
    "account:read",
)


class MondayOAuthProvider(OAuthProvider):
    name = "monday"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client_id = settings.monday_client_id.strip()
        self.client_secret = settings.monday_client_secret.strip()
        self.redirect_uri = settings.monday_redirect_uri.strip()
        self._timeout = settings.oauth_http_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def default_scopes(self) -> list[str]:
        return list(MONDAY_SCOPES)

    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        self._require_configured()
        scope_list = scopes or self.default_scopes()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(scope_list),
        }
        return f"{MONDAY_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokenSet:
        self._require_configured()
        try:
            response = httpx.post(
                MONDAY_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach monday.com token endpoint",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monday.com rejected the OAuth token request",
            )
        return self._to_token_set(response.json())

    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="monday.com access tokens cannot be refreshed — reconnect the account",
        )

    def fetch_profile(self, access_token: str) -> OAuthProfile:
        self._require_configured()
        query = """
        query {
          me { id name email }
          account { id name slug }
        }
        """
        try:
            response = httpx.post(
                MONDAY_API_URL,
                json={"query": query},
                headers={
                    "Authorization": access_token,
                    "Content-Type": "application/json",
                    "API-Version": "2024-10",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch monday.com profile",
            ) from exc

        payload = response.json()
        if payload.get("errors"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="monday.com profile query failed",
            )
        data = payload.get("data") or {}
        me = data.get("me") or {}
        account = data.get("account") or {}
        subject = str(me.get("id") or "")
        email = (me.get("email") or "").strip().lower()
        name = (me.get("name") or account.get("name") or "monday.com").strip()
        if not email:
            slug = (account.get("slug") or subject or "account").strip().lower()
            email = f"monday+{slug}@users.monday.local"
        if not subject:
            subject = email

        return OAuthProfile(
            subject=subject,
            email=email,
            email_verified=bool(me.get("email")),
            full_name=name[:255],
            given_name=(name.split()[0] if name else None),
            picture_url=None,
            raw={
                "me": me,
                "account": account,
                "workspace_id": str(account.get("id") or ""),
                "workspace_name": account.get("name") or "",
            },
        )

    def _to_token_set(self, data: dict) -> OAuthTokenSet:
        access = data.get("access_token")
        if not access:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="monday.com token response missing access_token",
            )
        scope = data.get("scope")
        if isinstance(scope, list):
            scope = " ".join(scope)
        return OAuthTokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=None,
            token_type=data.get("token_type") or "bearer",
            scope=scope,
            id_token=None,
            raw=data,
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="monday.com OAuth is not configured",
            )
