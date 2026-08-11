"""OAuth provider contracts — shared types for every identity provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class OAuthProfile:
    """Normalised identity returned after a successful provider handshake."""

    subject: str
    email: str
    email_verified: bool
    full_name: str
    given_name: str | None = None
    picture_url: str | None = None
    locale: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OAuthTokenSet:
    """Tokens returned by the provider token endpoint."""

    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    token_type: str = "Bearer"
    scope: str | None = None
    id_token: str | None = None
    raw: dict = field(default_factory=dict)
