"""Authenticated profile update + password change."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.main import app
from app.models import RefreshToken, User
from app.services.auth_service import AuthService
from app.services.demo_data import USER as DEMO_USER

client = TestClient(app)


def _cleanup(email: str) -> None:
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


def _seed_password_user(email: str, password: str = "correct-horse") -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            name="Pat",
            full_name="Pat Example",
            role="COO",
            company="Example Co",
            avatar="PE",
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


def _seed_oauth_user(email: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=None,
            name="OAuth",
            full_name="OAuth User",
            role="Founder",
            company="OAuth Co",
            avatar="OU",
            timezone="Europe/Athens",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _tokens(user_id) -> tuple[str, str]:
    db = SessionLocal()
    try:
        tokens = AuthService(db).issue_tokens(db.get(User, user_id))
        return tokens.accessToken, tokens.refreshToken
    finally:
        db.close()


def test_auth_me_returns_authenticated_profile_not_demo():
    email = f"prof-me-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_oauth_user(email)
        access, _ = _tokens(user.id)
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email.lower()
        assert data["fullName"] == "OAuth User"
        assert data["company"] == "OAuth Co"
        assert data["email"] != DEMO_USER["email"]
        assert data["fullName"] != DEMO_USER["fullName"]
    finally:
        _cleanup(email)


def test_profile_update_persists_and_returns_user():
    email = f"prof-up-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_oauth_user(email)
        access, _ = _tokens(user.id)
        headers = {"Authorization": f"Bearer {access}"}
        response = client.patch(
            "/settings/profile",
            headers=headers,
            json={
                "fullName": "Lydia Real",
                "role": "CEO",
                "company": "Real Systems",
                "timezone": "America/New_York",
                "avatar": "LR",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fullName"] == "Lydia Real"
        assert data["role"] == "CEO"
        assert data["company"] == "Real Systems"
        assert data["timezone"] == "America/New_York"
        assert data["avatar"] == "LR"
        assert data["email"] == email.lower()

        me = client.get("/auth/me", headers=headers).json()
        assert me["fullName"] == "Lydia Real"
        assert me["company"] == "Real Systems"

        db = SessionLocal()
        try:
            row = db.query(User).filter(User.email == email.lower()).one()
            assert row.full_name == "Lydia Real"
            assert row.company == "Real Systems"
            assert row.timezone == "America/New_York"
            assert row.avatar == "LR"
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_profile_update_persists_across_logout_login():
    email = f"prof-rel-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct-horse"
    try:
        user = _seed_password_user(email, password)
        access, refresh = _tokens(user.id)
        headers = {"Authorization": f"Bearer {access}"}
        client.patch(
            "/settings/profile",
            headers=headers,
            json={"fullName": "After Reload", "company": "Persist Co"},
        )
        client.post("/auth/logout", json={"refreshToken": refresh})
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        assert login.json()["user"]["fullName"] == "After Reload"
        assert login.json()["user"]["company"] == "Persist Co"
    finally:
        _cleanup(email)


def test_profile_update_unauthorized_without_token_when_auth_required(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "auth_required", True)
    response = client.patch(
        "/settings/profile",
        json={"fullName": "Nope"},
    )
    assert response.status_code == 401


def test_oauth_user_null_password_can_edit_profile_not_change_password():
    email = f"prof-oauth-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_oauth_user(email)
        access, _ = _tokens(user.id)
        headers = {"Authorization": f"Bearer {access}"}
        settings = client.get("/settings", headers=headers).json()
        assert settings["profile"]["hasPassword"] is False
        assert settings["security"]["hasPassword"] is False

        ok = client.patch(
            "/settings/profile",
            headers=headers,
            json={"fullName": "Google Only", "role": "Founder"},
        )
        assert ok.status_code == 200
        assert ok.json()["fullName"] == "Google Only"

        bad = client.post(
            "/settings/password",
            headers=headers,
            json={"currentPassword": "anything", "newPassword": "newpassword1"},
        )
        assert bad.status_code == 400
        assert "no password" in bad.json()["detail"].lower()
    finally:
        _cleanup(email)


def test_password_change_and_refresh_revocation():
    email = f"prof-pw-{uuid.uuid4().hex[:10]}@example.com"
    old_password = "correct-horse"
    new_password = "new-correct-battery"
    try:
        user = _seed_password_user(email, old_password)
        access, refresh = _tokens(user.id)
        # Second session
        access2, refresh2 = _tokens(user.id)
        headers = {"Authorization": f"Bearer {access}"}

        response = client.post(
            "/settings/password",
            headers=headers,
            json={"currentPassword": old_password, "newPassword": new_password},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Old refresh tokens revoked
        for token in (refresh, refresh2):
            denied = client.post("/auth/refresh", json={"refreshToken": token})
            assert denied.status_code == 401

        # Old password fails; new works
        assert (
            client.post("/auth/login", json={"email": email, "password": old_password}).status_code
            == 401
        )
        login = client.post("/auth/login", json={"email": email, "password": new_password})
        assert login.status_code == 200

        db = SessionLocal()
        try:
            row = db.query(User).filter(User.email == email.lower()).one()
            assert verify_password(new_password, row.hashed_password)
            assert "correct-horse" not in (row.hashed_password or "")
            active = (
                db.query(RefreshToken)
                .filter(RefreshToken.user_id == row.id, RefreshToken.revoked_at.is_(None))
                .count()
            )
            # login issued a fresh refresh token
            assert active >= 1
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_demo_mode_settings_still_available():
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["email"] == DEMO_USER["email"]
    assert data["profile"]["fullName"] == DEMO_USER["fullName"]
