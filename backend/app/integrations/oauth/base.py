"""Abstract OAuth provider — Authorization Code Flow only.

Concrete providers (Google, Notion; Microsoft / GoHighLevel later) implement
this interface. Domain services never call provider HTTP APIs directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import Settings
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet


class OAuthProvider(ABC):
    """One identity / data provider behind a stable internal interface."""

    name: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def is_configured(self) -> bool:
        """True when client id/secret/redirect are present."""

    @abstractmethod
    def default_scopes(self) -> list[str]:
        """Scopes requested for authentication (no data sync scopes here)."""

    @abstractmethod
    def build_authorization_url(self, *, state: str, scopes: list[str] | None = None) -> str:
        """Return the provider URL the browser should open."""

    @abstractmethod
    def exchange_code(self, code: str) -> OAuthTokenSet:
        """Exchange an authorization code for tokens."""

    @abstractmethod
    def refresh_tokens(self, refresh_token: str) -> OAuthTokenSet:
        """Refresh an expired access token."""

    @abstractmethod
    def fetch_profile(self, access_token: str) -> OAuthProfile:
        """Load the authenticated user's profile from the provider."""
