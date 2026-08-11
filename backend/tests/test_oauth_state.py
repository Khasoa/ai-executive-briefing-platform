"""OAuth CSRF state lifecycle — create, consume-once, expire, scoping."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.oauth.google import GoogleOAuthProvider
from app.integrations.oauth import types as oauth_types
from app.main import app
from app.models import Integration, OAuthLoginTicket, OAuthState, RefreshToken, User
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService, _as_utc

client = TestClient(app)


def _settings(**overrides):
    base = {
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/oauth/google/callback",
        "OAUTH_SUCCESS_REDIRECT": "",
        "OAUTH_STATE_EXPIRE_MINUTES": "10",
    }
    base.update(overrides)
    return base


def _apply_env(monkeypatch, **overrides):
    for key, value in _settings(**overrides).items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def _cleanup_email(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(Integration).filter(Integration.user_id == user.id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.query(OAuthLoginTicket).filter(OAuthLoginTicket.user_id == user.id).delete()
        db.query(OAuthState).filter(OAuthState.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=None,
            name="State",
            full_name="State User",
            role="CEO",
            company="Test",
            avatar="SU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _mock_google(monkeypatch, email: str):
    token_set = oauth_types.OAuthTokenSet(
        access_token="ya29.access",
        refresh_token="1//refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scope="openid email profile",
    )
    profile = oauth_types.OAuthProfile(
        subject=f"sub-{uuid.uuid4().hex[:8]}",
        email=email,
        email_verified=True,
        full_name="Google User",
        given_name="Google",
    )
    monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
    monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
    # Avoid real Google API calls from post-OAuth sync.
    monkeypatch.setattr(
        OAuthService,
        "_best_effort_google_sync",
        lambda self, user: None,
    )


def test_as_utc_normalises_naive_and_aware():
    naive = datetime(2026, 8, 10, 12, 0, 0)
    aware = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert _as_utc(naive).tzinfo == timezone.utc
    assert _as_utc(aware) == aware


def test_fresh_state_is_accepted(monkeypatch):
    email = f"state-ok-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        _mock_google(monkeypatch, email)
        start = client.get("/auth/oauth/google/start").json()
        state = start["state"]
        db = SessionLocal()
        try:
            row = db.query(OAuthState).filter(OAuthState.state == state).one()
            assert row.consumed_at is None
            assert _as_utc(row.expires_at) > datetime.now(timezone.utc)
            assert row.expires_at.tzinfo is not None
        finally:
            db.close()

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-1", "state": state},
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["email"] == email
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_valid_state_consumed_exactly_once(monkeypatch):
    email = f"state-once-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        _mock_google(monkeypatch, email)
        state = client.get("/auth/oauth/google/start").json()["state"]
        first = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-1", "state": state},
        )
        assert first.status_code == 200
        second = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-2", "state": state},
        )
        assert second.status_code == 400
        assert second.json()["detail"] == "Invalid OAuth state"
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_expired_state_rejected(monkeypatch):
    email = f"state-exp-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        _mock_google(monkeypatch, email)
        state = client.get("/auth/oauth/google/start").json()["state"]
        db = SessionLocal()
        try:
            row = db.query(OAuthState).filter(OAuthState.state == state).one()
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
            db.commit()
        finally:
            db.close()

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-1", "state": state},
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "OAuth state expired" in detail
        assert "10" in detail  # ttl minutes called out
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_unknown_state_rejected(monkeypatch):
    _apply_env(monkeypatch)
    try:
        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "x", "state": "totally-unknown-state-value"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid OAuth state"
    finally:
        get_settings.cache_clear()


def test_stale_state_invalidated_on_new_start(monkeypatch):
    """A second /start must invalidate the previous unused state (stale tab)."""
    email = f"state-stale-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        _mock_google(monkeypatch, email)
        first = client.get("/auth/oauth/google/start").json()["state"]
        second = client.get("/auth/oauth/google/start").json()["state"]
        assert first != second

        stale = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-old", "state": first},
        )
        assert stale.status_code == 400
        assert stale.json()["detail"] == "Invalid OAuth state"

        ok = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-new", "state": second},
        )
        assert ok.status_code == 200, ok.text
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_state_belongs_to_initiating_user(monkeypatch):
    email = f"state-link-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            token = AuthService(db).issue_tokens(db.get(User, user.id)).accessToken
        finally:
            db.close()

        _mock_google(monkeypatch, "other-google-identity@example.com")
        start = client.get(
            "/auth/oauth/google/start",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        state = start["state"]

        db = SessionLocal()
        try:
            row = db.query(OAuthState).filter(OAuthState.state == state).one()
            assert row.user_id == user.id
        finally:
            db.close()

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-1", "state": state},
        )
        assert response.status_code == 200
        # Linked to initiating user — not a new user from Google profile email.
        assert response.json()["user"]["email"] == email.lower()
    finally:
        _cleanup_email(email)
        _cleanup_email("other-google-identity@example.com")
        get_settings.cache_clear()


def test_expiration_comparison_uses_timezone_aware_utc(monkeypatch):
    email = f"state-tz-{uuid.uuid4().hex[:8]}@example.com"
    _apply_env(monkeypatch)
    try:
        _mock_google(monkeypatch, email)
        state = client.get("/auth/oauth/google/start").json()["state"]
        db = SessionLocal()
        try:
            row = db.query(OAuthState).filter(OAuthState.state == state).one()
            # Non-UTC offset that is already expired once normalised to UTC.
            plus3 = timezone(timedelta(hours=3))
            row.expires_at = datetime.now(plus3) - timedelta(hours=2)
            db.commit()
            db.refresh(row)
            assert _as_utc(row.expires_at) <= datetime.now(timezone.utc)
        finally:
            db.close()

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "code-1", "state": state},
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()
