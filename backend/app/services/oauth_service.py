"""OAuth orchestration — authorize, callback, find-or-create, token storage."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_token, new_refresh_token
from app.core.token_crypto import decrypt_secret, encrypt_secret
from app.integrations.oauth import get_oauth_provider
from app.integrations.oauth.types import OAuthProfile, OAuthTokenSet
from app.models import Integration, OAuthLoginTicket, OAuthState, User
from app.schemas.auth import TokenResponse
from app.schemas.oauth import (
    OAuthAuthorizeResponse,
    OAuthConnectionStatus,
    OAuthTicketExchangeRequest,
)
from app.schemas.user import UserSchema
from app.services.auth_service import AuthService
from app.services.demo_user import public_user_dict

logger = logging.getLogger("briefly.oauth")


def _as_utc(value: datetime) -> datetime:
    """Normalise DB/app datetimes to timezone-aware UTC for comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class OAuthService:
    PROVIDER_GOOGLE = "google"

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.auth = AuthService(db, self.settings)

    def start(self, provider_name: str, *, user: User | None = None) -> OAuthAuthorizeResponse:
        provider = get_oauth_provider(provider_name, self.settings)
        if not provider.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{provider.name} OAuth is not configured",
            )

        link_user_id = user.id if user is not None else None
        # Invalidate prior unused states for this provider + initiator so a stale
        # Google/Notion tab cannot complete against an abandoned authorize URL.
        self._invalidate_pending_states(provider.name, link_user_id)

        now = datetime.now(timezone.utc)
        state = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=self.settings.oauth_state_expire_minutes)
        self.db.add(
            OAuthState(
                state=state,
                provider=provider.name,
                user_id=link_user_id,
                expires_at=expires_at,
            )
        )
        self.db.commit()
        logger.info(
            "OAuth state issued provider=%s user=%s ttl_minutes=%s expires_at=%s",
            provider.name,
            link_user_id,
            self.settings.oauth_state_expire_minutes,
            expires_at.isoformat(),
        )

        return OAuthAuthorizeResponse(
            provider=provider.name,
            authorizationUrl=provider.build_authorization_url(state=state),
            state=state,
        )

    def handle_callback(
        self,
        provider_name: str,
        *,
        code: str | None,
        state: str | None,
        error: str | None = None,
    ) -> TokenResponse | str:
        """Complete the OAuth handshake.

        Returns a `TokenResponse` when no frontend redirect is configured,
        otherwise a redirect URL containing a one-time ticket.
        """
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth provider returned an error: {error}",
            )
        if not code or not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing OAuth code or state",
            )

        provider = get_oauth_provider(provider_name, self.settings)
        oauth_state = self._consume_state(provider.name, state)
        token_set = provider.exchange_code(code)
        if provider.name == "gohighlevel" and hasattr(provider, "profile_from_token_payload"):
            profile = provider.profile_from_token_payload(token_set)
        else:
            profile = provider.fetch_profile(token_set.access_token)
        user = self._find_or_create_user(profile, link_user_id=oauth_state.user_id)
        self._upsert_integration(user, provider.name, token_set, profile, provider.default_scopes())
        if provider.name == self.PROVIDER_GOOGLE:
            # Tokens live on provider=google; mirror sync writes Email/Meeting for
            # this same user_id so domain pages are not left on the demo tenant.
            self._best_effort_google_sync(user)
        tokens = self.auth.issue_tokens(user)

        redirect = self.settings.oauth_success_redirect.strip()
        if not redirect:
            return tokens

        ticket = self._issue_login_ticket(provider.name, user, tokens)
        separator = "&" if "?" in redirect else "?"
        return f"{redirect}{separator}{urlencode({'ticket': ticket, 'provider': provider.name})}"

    def exchange_ticket(
        self, payload: OAuthTicketExchangeRequest, *, provider: str | None = None
    ) -> TokenResponse:
        record = (
            self.db.query(OAuthLoginTicket)
            .filter(OAuthLoginTicket.ticket_hash == hash_token(payload.ticket))
            .first()
        )
        now = datetime.now(timezone.utc)
        if record is None or record.consumed_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or already used OAuth ticket",
            )
        if provider and record.provider and record.provider.lower() != provider.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth ticket does not match this provider",
            )
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth ticket expired",
            )

        record.consumed_at = now
        self.db.commit()
        data = record.payload
        return TokenResponse(
            accessToken=data["accessToken"],
            refreshToken=data["refreshToken"],
            tokenType=data.get("tokenType", "bearer"),
            expiresIn=data["expiresIn"],
            user=UserSchema(**data["user"]),
        )

    def connection_status(self, user: User, provider_name: str) -> OAuthConnectionStatus:
        provider = get_oauth_provider(provider_name, self.settings)
        row = self._get_integration(user.id, provider.name)
        if row is None or row.status != "connected":
            return OAuthConnectionStatus(
                provider=provider.name,
                connected=False,
                configured=provider.is_configured(),
            )
        meta = (row.config or {}).get("profile") or {}
        return OAuthConnectionStatus(
            provider=provider.name,
            connected=True,
            configured=provider.is_configured(),
            account=row.account,
            subject=meta.get("sub"),
            scopes=list(row.scopes or []),
            connectedAt=row.connected_at,
        )

    def refresh_provider_access_token(self, user: User, provider_name: str) -> str:
        """Refresh the provider access token if needed; return a usable access token."""
        provider = get_oauth_provider(provider_name, self.settings)
        row = self._get_integration(user.id, provider.name)
        if row is None or row.status != "connected":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{provider.name} is not connected for this user",
            )

        oauth = dict((row.config or {}).get("oauth") or {})
        access = self._decrypt_optional(oauth.get("access_token"))
        refresh = self._decrypt_optional(oauth.get("refresh_token"))
        expires_at = self._parse_expiry(oauth.get("expires_at"))

        skew = timedelta(seconds=60)
        now = datetime.now(timezone.utc)
        # Long-lived tokens (e.g. Notion) store expires_at=None and need no refresh.
        if access and (expires_at is None or expires_at - skew > now):
            return access

        if not refresh:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{provider.name} refresh token missing — reconnect required",
            )

        token_set = provider.refresh_tokens(refresh)
        profile_meta = (row.config or {}).get("profile") or {}
        profile = OAuthProfile(
            subject=str(profile_meta.get("sub") or ""),
            email=row.account or user.email,
            email_verified=bool(profile_meta.get("email_verified", False)),
            full_name=user.full_name,
            picture_url=profile_meta.get("picture"),
            raw=profile_meta,
        )
        # Preserve prior refresh token when provider omits a new one.
        if token_set.refresh_token is None:
            token_set = OAuthTokenSet(
                access_token=token_set.access_token,
                refresh_token=refresh,
                expires_at=token_set.expires_at,
                token_type=token_set.token_type,
                scope=token_set.scope or oauth.get("scope"),
                id_token=token_set.id_token,
                raw=token_set.raw,
            )
        self._upsert_integration(
            user,
            provider.name,
            token_set,
            profile,
            list(row.scopes or provider.default_scopes()),
        )
        return token_set.access_token

    def disconnect(self, user: User, provider_name: str) -> OAuthConnectionStatus:
        provider = get_oauth_provider(provider_name, self.settings)
        row = self._get_integration(user.id, provider.name)
        if row is not None:
            row.status = "not-connected"
            row.account = None
            row.scopes = []
            row.config = {}
            row.connected_at = None
            self.db.commit()
        return self.connection_status(user, provider.name)

    def _invalidate_pending_states(self, provider: str, user_id: UUID | None) -> None:
        """Mark prior unused states consumed so only the latest start is valid."""
        now = datetime.now(timezone.utc)
        query = self.db.query(OAuthState).filter(
            OAuthState.provider == provider,
            OAuthState.consumed_at.is_(None),
        )
        if user_id is None:
            query = query.filter(OAuthState.user_id.is_(None))
        else:
            query = query.filter(OAuthState.user_id == user_id)
        pending = query.all()
        for row in pending:
            row.consumed_at = now
        if pending:
            logger.info(
                "OAuth invalidated %s pending state(s) provider=%s user=%s",
                len(pending),
                provider,
                user_id,
            )

    def _consume_state(self, provider: str, state: str) -> OAuthState:
        record = (
            self.db.query(OAuthState)
            .filter(OAuthState.state == state, OAuthState.provider == provider)
            .first()
        )
        now = datetime.now(timezone.utc)
        if record is None:
            logger.info(
                "OAuth state unknown provider=%s state_prefix=%s",
                provider,
                (state or "")[:8],
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            )
        if record.consumed_at is not None:
            logger.info(
                "OAuth state already consumed provider=%s state_prefix=%s user=%s",
                provider,
                (state or "")[:8],
                record.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state",
            )

        expires_at = _as_utc(record.expires_at)
        if expires_at <= now:
            age_s = int((now - _as_utc(record.created_at or expires_at)).total_seconds())
            logger.info(
                "OAuth state expired provider=%s state_prefix=%s user=%s "
                "expires_at=%s now=%s age_seconds=%s ttl_minutes=%s",
                provider,
                (state or "")[:8],
                record.user_id,
                expires_at.isoformat(),
                now.isoformat(),
                age_s,
                self.settings.oauth_state_expire_minutes,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "OAuth state expired — start Connect again "
                    f"(states last {self.settings.oauth_state_expire_minutes} minutes)"
                ),
            )
        record.consumed_at = now
        self.db.commit()
        logger.info(
            "OAuth state consumed provider=%s state_prefix=%s user=%s",
            provider,
            (state or "")[:8],
            record.user_id,
        )
        return record

    def _best_effort_google_sync(self, user: User) -> None:
        """Pull Calendar/Gmail into this user's rows after Google OAuth succeeds."""
        try:
            from app.services.calendar_sync_service import CalendarSyncService

            CalendarSyncService(self.db, self.settings).sync_user(user, reason="oauth")
        except Exception:
            logger.warning(
                "Post-OAuth Google Calendar sync skipped for user %s",
                user.id,
                exc_info=True,
            )
        try:
            from app.services.gmail_sync_service import GmailSyncService

            GmailSyncService(self.db, self.settings).sync_user(user, reason="oauth")
        except Exception:
            logger.warning(
                "Post-OAuth Gmail sync skipped for user %s",
                user.id,
                exc_info=True,
            )

    def _find_or_create_user(
        self, profile: OAuthProfile, *, link_user_id: UUID | None
    ) -> User:
        if link_user_id is not None:
            linked = self.db.get(User, link_user_id)
            if linked is None or not linked.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot link OAuth account to inactive user",
                )
            # Prefer keeping the existing account email unless empty.
            return linked

        # Prefer subject match only for identity providers (Google). Workspace
        # bots (Notion) should link via `link_user_id` or email, not create
        # phantom users from synthesised @users.notion.local addresses alone.
        by_subject = self._find_user_by_provider_subject(self.PROVIDER_GOOGLE, profile.subject)
        if by_subject is not None:
            return by_subject

        existing = self.db.query(User).filter(User.email == profile.email).first()
        if existing is not None:
            if not existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This account is disabled",
                )
            return existing

        # Refuse to auto-provision from synthetic workspace emails.
        if profile.email.endswith("@users.notion.local"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect Notion while signed in to link it to your Briefly account",
            )
        if profile.email.endswith("@users.gohighlevel.local"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect GoHighLevel while signed in to link it to your Briefly account",
            )
        if profile.email.endswith("@users.monday.local"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect monday.com while signed in to link it to your Briefly account",
            )
        if profile.email.endswith("@users.clickup.local"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect ClickUp while signed in to link it to your Briefly account",
            )

        full_name = profile.full_name.strip() or profile.email.split("@")[0]
        given = (profile.given_name or full_name.split()[0]).strip()
        initials = "".join(part[0] for part in full_name.split()[:2]).upper() or "BR"
        user = User(
            email=profile.email,
            hashed_password=None,
            name=given[:100],
            full_name=full_name[:255],
            role="Executive",
            company="",
            avatar=initials[:10],
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _find_user_by_provider_subject(self, provider: str, subject: str) -> User | None:
        if not subject:
            return None
        row = (
            self.db.query(Integration)
            .filter(
                Integration.provider == provider,
                Integration.config.contains({"profile": {"sub": subject}}),
            )
            .first()
        )
        if row is None:
            return None
        return self.db.get(User, row.user_id)

    def _upsert_integration(
        self,
        user: User,
        provider: str,
        token_set: OAuthTokenSet,
        profile: OAuthProfile,
        scopes: list[str],
    ) -> Integration:
        row = self._get_integration(user.id, provider)
        now = datetime.now(timezone.utc)
        oauth_blob = {
            "access_token": encrypt_secret(token_set.access_token, self.settings),
            "token_type": token_set.token_type,
            "scope": token_set.scope or " ".join(scopes),
            "expires_at": token_set.expires_at.isoformat() if token_set.expires_at else None,
        }
        if token_set.refresh_token:
            oauth_blob["refresh_token"] = encrypt_secret(token_set.refresh_token, self.settings)
        elif row is not None:
            prior = ((row.config or {}).get("oauth") or {}).get("refresh_token")
            if prior:
                oauth_blob["refresh_token"] = prior

        profile_blob = {
            "sub": profile.subject,
            "email": profile.email,
            "email_verified": profile.email_verified,
            "name": profile.full_name,
            "picture": profile.picture_url,
            "locale": profile.locale,
        }
        if isinstance(profile.raw, dict):
            for key in (
                "workspace_id",
                "workspace_name",
                "location_id",
                "user_id",
                "company_id",
            ):
                if profile.raw.get(key):
                    profile_blob[key] = profile.raw[key]

        account = profile.email
        if provider == "notion":
            workspace = profile_blob.get("workspace_name") or profile.full_name
            if workspace:
                account = str(workspace)
        if provider == "gohighlevel":
            location = profile_blob.get("location_id") or profile.full_name
            if location:
                account = f"Location {location}" if profile_blob.get("location_id") else str(location)
        if provider == "monday":
            workspace = profile_blob.get("workspace_name") or profile.full_name
            if workspace:
                account = str(workspace)
        if provider == "clickup":
            workspace = profile_blob.get("workspace_name") or profile.full_name
            if workspace:
                account = str(workspace)

        # Preserve sync watermarks / display metadata across token writes.
        prior_config = dict(row.config or {}) if row is not None else {}
        display = _provider_display_defaults(provider)
        config = {
            **display,
            **{k: v for k, v in prior_config.items() if k not in ("oauth", "profile")},
            "oauth": oauth_blob,
            "profile": profile_blob,
        }
        if provider == "gohighlevel" and profile_blob.get("location_id"):
            ghl_meta = dict(config.get("ghl") or {})
            ghl_meta["location_id"] = profile_blob["location_id"]
            config["ghl"] = ghl_meta

        if row is None:
            row = Integration(
                user_id=user.id,
                provider=provider,
                status="connected",
                account=account,
                scopes=scopes,
                config=config,
                connected_at=now,
            )
            self.db.add(row)
        else:
            if "refresh_token" not in oauth_blob:
                prior = (prior_config.get("oauth") or {}).get("refresh_token")
                if prior:
                    oauth_blob["refresh_token"] = prior
                    config["oauth"] = oauth_blob
            row.status = "connected"
            row.account = account
            row.scopes = scopes
            row.config = config
            row.connected_at = row.connected_at or now

        self.db.commit()
        self.db.refresh(row)
        return row

    def _issue_login_ticket(self, provider: str, user: User, tokens: TokenResponse) -> str:
        ticket = new_refresh_token()
        self.db.add(
            OAuthLoginTicket(
                ticket_hash=hash_token(ticket),
                provider=provider,
                user_id=user.id,
                payload={
                    "accessToken": tokens.accessToken,
                    "refreshToken": tokens.refreshToken,
                    "tokenType": tokens.tokenType,
                    "expiresIn": tokens.expiresIn,
                    "user": public_user_dict(user),
                },
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=self.settings.oauth_ticket_expire_minutes),
            )
        )
        self.db.commit()
        return ticket

    def _get_integration(self, user_id: UUID, provider: str) -> Integration | None:
        return (
            self.db.query(Integration)
            .filter(Integration.user_id == user_id, Integration.provider == provider)
            .first()
        )

    def _decrypt_optional(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return decrypt_secret(value, self.settings)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored OAuth token could not be decrypted",
            ) from exc

    @staticmethod
    def _parse_expiry(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed


def _provider_display_defaults(provider: str) -> dict:
    if provider == "notion":
        return {
            "name": "Notion",
            "category": "Knowledge",
            "description": "Plans, metrics and documents that give the brief its internal context.",
            "metrics": [
                {"label": "Pages indexed", "value": "—"},
                {"label": "Databases", "value": "—"},
            ],
            "poweredBy": "Notion API",
        }
    if provider == "google":
        return {
            "name": "Google",
            "category": "Identity",
            "description": "Calendar and Gmail access for meetings and inbox intelligence.",
            "poweredBy": "Google Workspace API",
        }
    if provider == "gohighlevel":
        return {
            "name": "GoHighLevel",
            "category": "CRM",
            "description": "Opportunities, stages and interaction history behind pipeline intelligence.",
            "metrics": [
                {"label": "Opportunities", "value": "—"},
                {"label": "Pipeline", "value": "—"},
            ],
            "poweredBy": "GoHighLevel API",
        }
    if provider == "monday":
        return {
            "name": "monday.com",
            "category": "Work management",
            "description": "Boards, tasks and deadlines that show what needs executive attention.",
            "metrics": [
                {"label": "Items synced", "value": "—"},
                {"label": "Boards", "value": "—"},
            ],
            "poweredBy": "monday.com API",
        }
    if provider == "clickup":
        return {
            "name": "ClickUp",
            "category": "Work management",
            "description": "Tasks, priorities and owners across authorized ClickUp workspaces.",
            "metrics": [
                {"label": "Tasks synced", "value": "—"},
                {"label": "Workspaces", "value": "—"},
            ],
            "poweredBy": "ClickUp API",
        }
    return {"name": provider}
