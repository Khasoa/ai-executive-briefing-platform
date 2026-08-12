"""Provider registry — resolve OAuth implementations by name."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.integrations.oauth.base import OAuthProvider
from app.integrations.oauth.clickup import ClickUpOAuthProvider
from app.integrations.oauth.google import GoogleOAuthProvider
from app.integrations.oauth.gohighlevel import GoHighLevelOAuthProvider
from app.integrations.oauth.monday import MondayOAuthProvider
from app.integrations.oauth.notion import NotionOAuthProvider

_PROVIDERS: dict[str, type[OAuthProvider]] = {
    GoogleOAuthProvider.name: GoogleOAuthProvider,
    NotionOAuthProvider.name: NotionOAuthProvider,
    GoHighLevelOAuthProvider.name: GoHighLevelOAuthProvider,
    MondayOAuthProvider.name: MondayOAuthProvider,
    ClickUpOAuthProvider.name: ClickUpOAuthProvider,
}


def list_oauth_providers() -> list[str]:
    return sorted(_PROVIDERS)


def get_oauth_provider(name: str, settings: Settings | None = None) -> OAuthProvider:
    key = name.strip().lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown OAuth provider '{name}'",
        )
    return cls(settings or get_settings())
