from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db as _get_db
from app.models import User
from app.services.auth_service import AuthService
from app.services.demo_user import get_or_create_demo_user

# auto_error=False so missing Bearer falls through to the demo user when
# AUTH_REQUIRED is false (portfolio / local default).
_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Re-export database session dependency for route modules."""
    yield from _get_db()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Resolve the request user.

    - Valid Bearer access token → that user
    - Missing token + `auth_required=False` → demo user (unchanged demo mode)
    - Missing/invalid token + `auth_required=True` → 401
    """
    settings = get_settings()

    if credentials is not None:
        return AuthService(db, settings).resolve_access_token(credentials.credentials)

    if settings.auth_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return get_or_create_demo_user(db)


def get_current_user_required(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Strict auth — used by `/auth/me` when a token is expected for clarity.

    Still accepts the demo fallback when `auth_required` is false and no
    token is sent, so `GET /auth/me` works in the portfolio demo.
    """
    return get_current_user(db=db, credentials=credentials)


DbSession = Depends(get_db)
CurrentUser = Annotated[User, Depends(get_current_user)]
