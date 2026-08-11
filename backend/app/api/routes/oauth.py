"""OAuth routes — Authorization Code Flow against registered providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.auth import TokenResponse
from app.schemas.oauth import (
    OAuthAuthorizeResponse,
    OAuthConnectionStatus,
    OAuthProviderTokenResponse,
    OAuthTicketExchangeRequest,
)
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])
_bearer = HTTPBearer(auto_error=False)


def _optional_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    """Resolve Bearer user when present; never fall back to the demo user.

    Used only for "link Google to my existing session" on authorize start.
    """
    if credentials is None:
        return None
    return AuthService(db).resolve_access_token(credentials.credentials)


@router.get("/{provider}/start", response_model=OAuthAuthorizeResponse)
def start_oauth(
    provider: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
) -> OAuthAuthorizeResponse:
    """Begin Authorization Code Flow — returns the provider authorize URL."""
    return OAuthService(db).start(provider, user=user)


@router.get("/{provider}/callback")
def oauth_callback(
    provider: str,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
):
    """Google (etc.) redirects here after consent.

    When `OAUTH_SUCCESS_REDIRECT` is set, responds with 302 + one-time ticket.
    Otherwise returns the same `TokenResponse` as password login.
    """
    result = OAuthService(db).handle_callback(
        provider, code=code, state=state, error=error
    )
    if isinstance(result, str):
        return RedirectResponse(url=result, status_code=status.HTTP_302_FOUND)
    return result


@router.post("/{provider}/exchange", response_model=TokenResponse)
def exchange_oauth_ticket(
    provider: str,
    payload: OAuthTicketExchangeRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a one-time callback ticket for Briefly JWT + refresh tokens."""
    return OAuthService(db).exchange_ticket(payload, provider=provider)


@router.get("/{provider}/status", response_model=OAuthConnectionStatus)
def oauth_status(
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OAuthConnectionStatus:
    return OAuthService(db).connection_status(user, provider)


@router.post("/{provider}/refresh", response_model=OAuthProviderTokenResponse)
def refresh_provider_token(
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OAuthProviderTokenResponse:
    """Refresh the *provider* access token (not the Briefly JWT)."""
    access = OAuthService(db).refresh_provider_access_token(user, provider)
    return OAuthProviderTokenResponse(provider=provider, accessToken=access)


@router.post("/{provider}/disconnect", response_model=OAuthConnectionStatus)
def disconnect_oauth(
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OAuthConnectionStatus:
    return OAuthService(db).disconnect(user, provider)
