"""Password login, refresh-token rotation, and access-token resolution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserSchema
from app.services.demo_user import public_user_dict


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def register(self, payload: RegisterRequest) -> TokenResponse:
        existing = self.db.query(User).filter(User.email == payload.email.lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists",
            )

        full_name = payload.fullName.strip()
        name = (payload.name or full_name.split()[0]).strip()
        initials = "".join(part[0] for part in full_name.split()[:2]).upper() or "BR"

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            name=name,
            full_name=full_name,
            role=payload.role,
            company=payload.company,
            avatar=initials[:10],
            timezone=payload.timezone,
            is_active=True,
            preferences={},
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._issue_tokens(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.db.query(User).filter(User.email == payload.email.lower()).first()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled",
            )
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        record = self._get_valid_refresh_record(refresh_token)
        user = self.db.get(User, record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        record.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        return self._issue_tokens(user)

    def logout(self, refresh_token: str) -> None:
        record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_token(refresh_token))
            .first()
        )
        if record and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def issue_tokens(self, user: User) -> TokenResponse:
        """Public wrapper used by OAuth and other identity providers."""
        return self._issue_tokens(user)

    def resolve_access_token(self, token: str) -> User:
        payload = decode_access_token(token, self.settings)
        try:
            user_id = UUID(payload["sub"])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def _issue_tokens(self, user: User) -> TokenResponse:
        access_token, expires_in = create_access_token(
            subject=user.id,
            settings=self.settings,
            extra_claims={"email": user.email},
        )
        refresh = new_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=self.settings.refresh_token_expire_days),
            )
        )
        self.db.commit()
        return TokenResponse(
            accessToken=access_token,
            refreshToken=refresh,
            expiresIn=expires_in,
            user=UserSchema(**public_user_dict(user)),
        )

    def _get_valid_refresh_record(self, refresh_token: str) -> RefreshToken:
        record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_token(refresh_token))
            .first()
        )
        if record is None or record.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        return record
