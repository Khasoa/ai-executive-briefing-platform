"""GoHighLevel (LeadConnector) OAuth2 Authorization Code provider.

Auth URL: marketplace chooselocation flow.
Token URL: services.leadconnectorhq.com/oauth/token
Access tokens expire (~24h) and are refreshed with refresh_token.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet

GHL_AUTH_URL = "https://marketplace.gohighlevel.com/oauth/chooselocation"
GHL_TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"
GHL_VERSION = "2021-07-28"

GHL_SCOPES = (
    "opportunities.readonly",
    "contacts.readonly",
    "locations.readonly",
)


class GoHighLevelOAuthProvider(OAuthProvider):
    name = "gohighlevel"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client_id = settings.ghl_client_id.strip()
        self.client_secret = settings.ghl_client_secret.strip()
        self.redirect_uri = settings.ghl_redirect_uri.strip()
        self._timeout = settings.oauth_http_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def default_scopes(self) -> list[str]:
        return list(GHL_SCOPES)

    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        self._require_configured()
        params = {
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "scope": " ".join(scopes or self.default_scopes()),
            "state": state,
        }
        return f"{GHL_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthTokenSet:
        self._require_configured()
        data = self._token_request(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "user_type": "Location",
            }
        )
        return self._to_token_set(data)

    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        self._require_configured()
        data = self._token_request(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "user_type": "Location",
            }
        )
        if "refresh_token" not in data:
            data = {**data, "refresh_token": refresh_token}
        return self._to_token_set(data)

    def fetch_profile(self, access_token: str) -> OAuthProfile:
        """Build a profile from the token exchange payload stored in raw.

        GHL does not expose a Google-style userinfo endpoint for location tokens.
        Location/user identifiers arrive on the token response; callers pass them
        via `raw` when available. When only an access token is present, synthesise
        a stable subject.
        """
        _ = access_token
        # Profile enrichment happens in OAuthService after exchange using token raw.
        # This method is invoked with access token only — return a placeholder that
        # OAuthService overlays with token.raw fields when present.
        return OAuthProfile(
            subject="ghl-pending",
            email="ghl+pending@users.gohighlevel.local",
            email_verified=False,
            full_name="GoHighLevel location",
            raw={},
        )

    def profile_from_token_payload(self, token_set: OAuthTokenSet) -> OAuthProfile:
        """Preferred profile builder using the token endpoint payload."""
        raw = dict(token_set.raw or {})
        location_id = str(raw.get("locationId") or raw.get("location_id") or "").strip()
        user_id = str(raw.get("userId") or raw.get("user_id") or "").strip()
        company_id = str(raw.get("companyId") or raw.get("company_id") or "").strip()
        subject = user_id or location_id or "ghl-unknown"
        email = (raw.get("email") or "").strip().lower()
        if not email:
            handle = (location_id or subject).lower().replace(" ", "-")
            email = f"ghl+{handle}@users.gohighlevel.local"
        name = (
            raw.get("userName")
            or raw.get("locationName")
            or (f"GHL {location_id}" if location_id else "GoHighLevel")
        )
        return OAuthProfile(
            subject=subject,
            email=email,
            email_verified=bool(raw.get("email")),
            full_name=str(name)[:255],
            given_name=str(name).split()[0] if name else None,
            raw={
                **raw,
                "location_id": location_id,
                "user_id": user_id,
                "company_id": company_id,
            },
        )

    def _token_request(self, form: dict[str, str]) -> dict:
        try:
            response = httpx.post(
                GHL_TOKEN_URL,
                data=form,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach GoHighLevel token endpoint",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GoHighLevel rejected the OAuth token request",
            )
        return response.json()

    def _to_token_set(self, data: dict) -> OAuthTokenSet:
        access = data.get("access_token")
        if not access:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GoHighLevel token response missing access_token",
            )
        expires_in = data.get("expires_in")
        expires_at = None
        if expires_in is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        return OAuthTokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type") or "Bearer",
            scope=data.get("scope"),
            id_token=None,
            raw=data,
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GoHighLevel OAuth is not configured",
            )
