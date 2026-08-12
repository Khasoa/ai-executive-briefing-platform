"""Google OAuth Authorization Code Flow — identity only."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import decrypt_secret, encrypt_secret
from app.db.session import SessionLocal
from app.integrations.oauth.google import GOOGLE_AUTH_URL, GoogleOAuthProvider
from app.main import app
from app.models import Integration, OAuthLoginTicket, OAuthState, RefreshToken, User
from app.services.demo_data import USER as DEMO_PROFILE
from app.services.oauth_service import OAuthService

client = TestClient(app)


def _mute_post_oauth_sync(monkeypatch) -> None:
    monkeypatch.setattr(OAuthService, "_best_effort_google_sync", lambda self, user: None)


def _settings(**overrides):
    get_settings.cache_clear()
    base = {
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/oauth/google/callback",
        "OAUTH_SUCCESS_REDIRECT": "",
    }
    base.update(overrides)
    return base


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


def test_google_start_requires_configuration(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    get_settings.cache_clear()
    try:
        response = client.get("/auth/oauth/google/start")
        assert response.status_code == 503
    finally:
        get_settings.cache_clear()


def test_google_start_returns_authorization_url(monkeypatch):
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        response = client.get("/auth/oauth/google/start")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "google"
        assert data["state"]
        assert data["authorizationUrl"].startswith(GOOGLE_AUTH_URL)
        parsed = urlparse(data["authorizationUrl"])
        params = parse_qs(parsed.query)
        assert params["client_id"] == ["test-google-client-id"]
        assert params["response_type"] == ["code"]
        assert params["access_type"] == ["offline"]
        assert "openid" in params["scope"][0]
        assert "calendar.readonly" in params["scope"][0]
        assert "gmail.readonly" in params["scope"][0]
        assert params["state"] == [data["state"]]

        db = SessionLocal()
        try:
            row = db.query(OAuthState).filter(OAuthState.state == data["state"]).one()
            assert row.provider == "google"
            assert row.consumed_at is None
        finally:
            db.close()
    finally:
        get_settings.cache_clear()


def test_google_callback_issues_briefly_tokens(monkeypatch):
    email = f"google-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    try:
        start = client.get("/auth/oauth/google/start").json()
        state = start["state"]

        from app.integrations.oauth import types as oauth_types

        token_set = oauth_types.OAuthTokenSet(
            access_token="ya29.access",
            refresh_token="1//refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scope="openid email profile",
        )
        profile = oauth_types.OAuthProfile(
            subject=f"google-sub-{uuid.uuid4().hex[:8]}",
            email=email,
            email_verified=True,
            full_name="Google User",
            given_name="Google",
        )

        monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
        _mute_post_oauth_sync(monkeypatch)

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "auth-code-1", "state": state},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["accessToken"]
        assert body["refreshToken"]
        assert body["user"]["email"] == email
        assert body["user"]["fullName"] == "Google User"

        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {body['accessToken']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).one()
            assert user.hashed_password is None
            integration = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert integration.status == "connected"
            assert integration.account == email
            assert "openid" in integration.scopes
            oauth = integration.config["oauth"]
            assert decrypt_secret(oauth["access_token"]) == "ya29.access"
            assert decrypt_secret(oauth["refresh_token"]) == "1//refresh"
            assert integration.config["profile"]["sub"] == profile.subject

            consumed = db.query(OAuthState).filter(OAuthState.state == state).one()
            assert consumed.consumed_at is not None
        finally:
            db.close()

        # Replayed state must fail
        replay = client.get(
            "/auth/oauth/google/callback",
            params={"code": "auth-code-1", "state": state},
        )
        assert replay.status_code == 400
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_google_callback_rejects_invalid_state(monkeypatch):
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "x", "state": "not-a-real-state"},
        )
        assert response.status_code == 400
    finally:
        get_settings.cache_clear()


def test_oauth_ticket_redirect_and_exchange(monkeypatch):
    email = f"ticket-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings(
        OAUTH_SUCCESS_REDIRECT="http://localhost:5173/oauth/callback"
    ).items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    from app.integrations.oauth import types as oauth_types

    try:
        start = client.get("/auth/oauth/google/start").json()
        token_set = oauth_types.OAuthTokenSet(
            access_token="ya29.access-2",
            refresh_token="1//refresh-2",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        profile = oauth_types.OAuthProfile(
            subject=f"sub-{uuid.uuid4().hex[:8]}",
            email=email,
            email_verified=True,
            full_name="Ticket User",
        )
        monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
        _mute_post_oauth_sync(monkeypatch)

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "c", "state": start["state"]},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith("http://localhost:5173/oauth/callback?")
        ticket = parse_qs(urlparse(location).query)["ticket"][0]
        assert parse_qs(urlparse(location).query)["provider"][0] == "google"

        exchanged = client.post(
            "/auth/oauth/google/exchange",
            json={"ticket": ticket},
        )
        assert exchanged.status_code == 200
        body = exchanged.json()
        assert body["user"]["email"] == email
        assert body["accessToken"]
        assert body["refreshToken"]

        # Successful Google OAuth leaves the user authenticated.
        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {body['accessToken']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email

        reused = client.post(
            "/auth/oauth/google/exchange",
            json={"ticket": ticket},
        )
        assert reused.status_code == 401
        assert "already used" in reused.json()["detail"].lower() or "invalid" in reused.json()[
            "detail"
        ].lower()
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_oauth_expired_ticket_is_rejected(monkeypatch):
    email = f"expired-ticket-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings(
        OAUTH_SUCCESS_REDIRECT="http://localhost:5173/oauth/callback",
        OAUTH_TICKET_EXPIRE_MINUTES="2",
    ).items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    from app.core.security import hash_token
    from app.integrations.oauth import types as oauth_types

    try:
        start = client.get("/auth/oauth/google/start").json()
        token_set = oauth_types.OAuthTokenSet(
            access_token="ya29.access-exp",
            refresh_token="1//refresh-exp",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        profile = oauth_types.OAuthProfile(
            subject=f"sub-{uuid.uuid4().hex[:8]}",
            email=email,
            email_verified=True,
            full_name="Expired Ticket User",
        )
        monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
        _mute_post_oauth_sync(monkeypatch)

        response = client.get(
            "/auth/oauth/google/callback",
            params={"code": "c-exp", "state": start["state"]},
            follow_redirects=False,
        )
        ticket = parse_qs(urlparse(response.headers["location"]).query)["ticket"][0]

        db = SessionLocal()
        try:
            row = (
                db.query(OAuthLoginTicket)
                .filter(OAuthLoginTicket.ticket_hash == hash_token(ticket))
                .first()
            )
            assert row is not None
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
            db.commit()
        finally:
            db.close()

        expired = client.post(
            "/auth/oauth/google/exchange",
            json={"ticket": ticket},
        )
        assert expired.status_code == 401
        assert "expired" in expired.json()["detail"].lower()
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_provider_token_refresh_and_status(monkeypatch):
    email = f"refresh-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    from app.integrations.oauth import types as oauth_types

    try:
        start = client.get("/auth/oauth/google/start").json()
        token_set = oauth_types.OAuthTokenSet(
            access_token="ya29.old",
            refresh_token="1//refresh-keep",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        profile = oauth_types.OAuthProfile(
            subject=f"sub-{uuid.uuid4().hex[:8]}",
            email=email,
            email_verified=True,
            full_name="Refresh User",
        )
        monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
        _mute_post_oauth_sync(monkeypatch)

        tokens = client.get(
            "/auth/oauth/google/callback",
            params={"code": "c", "state": start["state"]},
        ).json()
        headers = {"Authorization": f"Bearer {tokens['accessToken']}"}

        status_before = client.get("/auth/oauth/google/status", headers=headers)
        assert status_before.status_code == 200
        assert status_before.json()["connected"] is True
        assert status_before.json()["account"] == email

        refreshed_set = oauth_types.OAuthTokenSet(
            access_token="ya29.new",
            refresh_token=None,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        monkeypatch.setattr(
            GoogleOAuthProvider, "refresh_tokens", lambda self, refresh: refreshed_set
        )

        refreshed = client.post("/auth/oauth/google/refresh", headers=headers)
        assert refreshed.status_code == 200
        assert refreshed.json()["accessToken"] == "ya29.new"

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).one()
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert decrypt_secret(row.config["oauth"]["access_token"]) == "ya29.new"
            assert decrypt_secret(row.config["oauth"]["refresh_token"]) == "1//refresh-keep"
        finally:
            db.close()

        disconnected = client.post("/auth/oauth/google/disconnect", headers=headers)
        assert disconnected.status_code == 200
        assert disconnected.json()["connected"] is False
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def test_demo_mode_unaffected_without_google(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    get_settings.cache_clear()
    try:
        response = client.get("/workspace")
        assert response.status_code == 200
        assert response.json()["user"]["email"] == DEMO_PROFILE["email"]
    finally:
        get_settings.cache_clear()


def test_token_crypto_roundtrip():
    settings = get_settings()
    encrypted = encrypt_secret("super-secret", settings)
    assert encrypted != "super-secret"
    assert decrypt_secret(encrypted, settings) == "super-secret"


def test_find_or_create_links_existing_password_user(monkeypatch):
    email = f"link-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    from app.integrations.oauth import types as oauth_types

    try:
        registered = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "secure-pass-99",
                "fullName": "Existing User",
            },
        )
        assert registered.status_code == 201

        start = client.get("/auth/oauth/google/start").json()
        token_set = oauth_types.OAuthTokenSet(
            access_token="ya29.link",
            refresh_token="1//link",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        profile = oauth_types.OAuthProfile(
            subject=f"sub-{uuid.uuid4().hex[:8]}",
            email=email,
            email_verified=True,
            full_name="Existing User",
        )
        monkeypatch.setattr(GoogleOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(GoogleOAuthProvider, "fetch_profile", lambda self, token: profile)
        _mute_post_oauth_sync(monkeypatch)

        body = client.get(
            "/auth/oauth/google/callback",
            params={"code": "c", "state": start["state"]},
        ).json()
        assert body["user"]["email"] == email

        db = SessionLocal()
        try:
            users = db.query(User).filter(User.email == email).all()
            assert len(users) == 1
            assert users[0].hashed_password is not None
        finally:
            db.close()
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()
