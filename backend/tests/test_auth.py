"""Authentication foundation — login, tokens, demo fallback, ownership."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import SessionLocal
from app.main import app
from app.models import RefreshToken, User
from app.services.demo_data import USER as DEMO_PROFILE

client = TestClient(app)


def _unique_email(prefix: str = "auth") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def _register(email: str | None = None, password: str = "secure-pass-99") -> dict:
    email = email or _unique_email()
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "fullName": "Test Executive",
            "name": "Test",
            "role": "CEO",
            "company": "Test Co",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["_email"] = email
    data["_password"] = password
    return data


def _cleanup_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def test_password_hash_roundtrip():
    hashed = hash_password("briefly-demo")
    assert hashed != "briefly-demo"
    assert verify_password("briefly-demo", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("briefly-demo", None)


def test_access_token_roundtrip():
    settings = get_settings()
    subject = uuid.uuid4()
    token, expires_in = create_access_token(subject=subject, settings=settings)
    assert expires_in == settings.access_token_expire_minutes * 60
    payload = decode_access_token(token, settings)
    assert payload["sub"] == str(subject)
    assert payload["type"] == "access"


def test_unauthenticated_me_returns_demo_user():
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == DEMO_PROFILE["email"]
    assert data["fullName"] == DEMO_PROFILE["fullName"]
    assert data["avatar"] == DEMO_PROFILE["avatar"]


def test_unauthenticated_workspace_still_uses_demo_user():
    response = client.get("/workspace")
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["email"] == DEMO_PROFILE["email"]
    assert user["name"] == DEMO_PROFILE["name"]


def test_register_login_me_refresh_logout_flow():
    email = _unique_email("flow")
    try:
        registered = _register(email=email)
        assert registered["tokenType"] == "bearer"
        assert registered["accessToken"]
        assert registered["refreshToken"]
        assert registered["expiresIn"] > 0
        assert registered["user"]["email"] == email
        assert registered["user"]["fullName"] == "Test Executive"

        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {registered['accessToken']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email

        login = client.post(
            "/auth/login",
            json={"email": email, "password": registered["_password"]},
        )
        assert login.status_code == 200
        login_body = login.json()
        assert login_body["user"]["email"] == email

        refreshed = client.post(
            "/auth/refresh",
            json={"refreshToken": login_body["refreshToken"]},
        )
        assert refreshed.status_code == 200
        new_tokens = refreshed.json()
        assert new_tokens["accessToken"]
        assert new_tokens["refreshToken"] != login_body["refreshToken"]

        # Rotated refresh token is single-use
        reuse = client.post(
            "/auth/refresh",
            json={"refreshToken": login_body["refreshToken"]},
        )
        assert reuse.status_code == 401

        logout = client.post(
            "/auth/logout",
            json={"refreshToken": new_tokens["refreshToken"]},
        )
        assert logout.status_code == 204

        after_logout = client.post(
            "/auth/refresh",
            json={"refreshToken": new_tokens["refreshToken"]},
        )
        assert after_logout.status_code == 401
    finally:
        _cleanup_user(email)


def test_login_rejects_bad_password():
    email = _unique_email("badpw")
    try:
        _register(email=email, password="correct-horse")
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert response.status_code == 401
    finally:
        _cleanup_user(email)


def test_register_rejects_duplicate_email():
    email = _unique_email("dup")
    try:
        _register(email=email)
        again = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "another-pass-99",
                "fullName": "Other Person",
            },
        )
        assert again.status_code == 409
    finally:
        _cleanup_user(email)


def test_invalid_access_token_is_rejected():
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401


def test_bearer_scopes_empty_crm_for_new_user():
    """Non-demo users must not inherit curated demo pipeline data."""
    email = _unique_email("scope")
    try:
        tokens = _register(email=email)
        response = client.get(
            "/crm",
            headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        )
        assert response.status_code == 200
        assert response.json()["opportunities"] == []
    finally:
        _cleanup_user(email)


def test_auth_required_blocks_missing_bearer(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    get_settings.cache_clear()
    try:
        # Recreate app settings for this process — TestClient uses the
        # already-imported app, but get_current_user calls get_settings().
        response = client.get("/workspace")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
    finally:
        monkeypatch.delenv("AUTH_REQUIRED", raising=False)
        get_settings.cache_clear()


def test_demo_user_can_login_with_default_password():
    """Demo account gets a password so portfolio login demos work."""
    response = client.post(
        "/auth/login",
        json={
            "email": DEMO_PROFILE["email"],
            "password": get_settings().demo_user_password,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == DEMO_PROFILE["email"]
    assert body["accessToken"]

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['accessToken']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == DEMO_PROFILE["email"]

    client.post("/auth/logout", json={"refreshToken": body["refreshToken"]})
