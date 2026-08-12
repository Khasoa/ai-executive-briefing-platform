"""Google OAuth2 Authorization Code provider.

Requests OpenID profile scopes plus Calendar and Gmail readonly so sync
phases can reuse one connected Google account.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.integrations.gmail import GMAIL_READONLY_SCOPE
from app.integrations.google_calendar import CALENDAR_READONLY_SCOPE
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

GOOGLE_AUTH_SCOPES = (
    "openid",
    "email",
    "profile",
    CALENDAR_READONLY_SCOPE,
    GMAIL_READONLY_SCOPE,
)


class GoogleOAuthProvider(OAuthProvider):
    name = "google"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client_id = settings.google_client_id.strip()
        self.client_secret = settings.google_client_secret.strip()
        self.redirect_uri = settings.google_redirect_uri.strip()
        self._timeout = settings.oauth_http_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def default_scopes(self) -> list[str]:
        return list(GOOGLE_AUTH_SCOPES)

    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        self._require_configured()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.default_scopes()),
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokenSet:
        self._require_configured()
        data = self._token_request(
            {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        return self._to_token_set(data)

    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        self._require_configured()
        data = self._token_request(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )
        # Google omits refresh_token on refresh responses — keep the old one.
        if "refresh_token" not in data:
            data = {**data, "refresh_token": refresh_token}
        return self._to_token_set(data)

    def fetch_profile(self, access_token: str) -> OAuthProfile:
        self._require_configured()
        try:
            response = httpx.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch Google profile",
            ) from exc

        raw = response.json()
        email = (raw.get("email") or "").strip().lower()
        if not email or not raw.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google profile did not include email and subject",
            )

        full_name = (raw.get("name") or email.split("@")[0]).strip()
        return OAuthProfile(
            subject=str(raw["sub"]),
            email=email,
            email_verified=bool(raw.get("email_verified", False)),
            full_name=full_name,
            given_name=(raw.get("given_name") or None),
            picture_url=(raw.get("picture") or None),
            locale=(raw.get("locale") or None),
            raw=raw,
        )

    def _token_request(self, form: dict[str, str]) -> dict:
        try:
            response = httpx.post(
                GOOGLE_TOKEN_URL,
                data=form,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach Google token endpoint",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google rejected the OAuth token request",
            )
        return response.json()

    def _to_token_set(self, data: dict) -> OAuthTokenSet:
        access = data.get("access_token")
        if not access:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google token response missing access_token",
            )
        expires_in = data.get("expires_in")
        expires_at = None
        if expires_in is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        return OAuthTokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type") or "Bearer",
            scope=data.get("scope"),
            id_token=data.get("id_token"),
            raw=data,
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured",
            )
