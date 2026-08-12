"""OAuth provider isolation — connecting one must not mutate siblings."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import hash_token
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.main import app
from app.models import Integration, OAuthLoginTicket, RefreshToken, User
from app.services.auth_service import AuthService

client = TestClient(app)


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(OAuthLoginTicket).filter(OAuthLoginTicket.user_id == user.id).delete()
        db.query(Integration).filter(Integration.user_id == user.id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
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
            name="Iso",
            full_name="Isolation User",
            role="CEO",
            company="Test",
            avatar="IU",
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


def _token(user_id) -> str:
    db = SessionLocal()
    try:
        return AuthService(db).issue_tokens(db.get(User, user_id)).accessToken
    finally:
        db.close()


def test_connecting_notion_does_not_connect_unrelated_providers():
    email = f"iso-notion-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="notion",
                    status="connected",
                    account="Notion Workspace",
                    scopes=["read_content"],
                    config={
                        "name": "Notion",
                        "oauth": {
                            "access_token": encrypt_secret("ntn_x", settings),
                        },
                    },
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        token = _token(user.id)
        listing = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        by_id = {i["id"]: i for i in listing["integrations"]}
        assert by_id["notion"]["status"] == "connected"
        for sibling in ("gohighlevel", "monday", "clickup"):
            assert by_id[sibling]["status"] == "not-connected"
            assert by_id[sibling]["account"] is None
        # Google family remains disconnected unless google OAuth exists.
        assert by_id["gmail"]["status"] == "not-connected"
        assert by_id["google-calendar"]["status"] == "not-connected"
    finally:
        _cleanup(email)


def test_google_still_projects_to_gmail_and_calendar():
    email = f"iso-google-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="google",
                    status="connected",
                    account=email,
                    scopes=["calendar.readonly", "gmail.readonly"],
                    config={
                        "name": "Google",
                        "oauth": {
                            "access_token": encrypt_secret("ya29.x", settings),
                            "refresh_token": encrypt_secret("1//x", settings),
                        },
                    },
                    connected_at=datetime.now(timezone.utc),
                    last_sync_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        token = _token(user.id)
        by_id = {
            i["id"]: i
            for i in client.get(
                "/integrations",
                headers={"Authorization": f"Bearer {token}"},
            ).json()["integrations"]
        }
        assert by_id["gmail"]["status"] == "connected"
        assert by_id["google-calendar"]["status"] == "connected"
        assert by_id["notion"]["status"] == "not-connected"
        assert by_id["clickup"]["status"] == "not-connected"
    finally:
        _cleanup(email)


def test_oauth_ticket_rejects_provider_mismatch():
    email = f"iso-ticket-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        raw_ticket = f"ticket-{uuid.uuid4().hex}"
        db = SessionLocal()
        try:
            tokens = AuthService(db).issue_tokens(db.get(User, user.id))
            db.add(
                OAuthLoginTicket(
                    ticket_hash=hash_token(raw_ticket),
                    provider="notion",
                    user_id=user.id,
                    payload={
                        "accessToken": tokens.accessToken,
                        "refreshToken": tokens.refreshToken,
                        "tokenType": "bearer",
                        "expiresIn": 3600,
                        "user": {
                            "email": user.email,
                            "name": user.name,
                            "fullName": user.full_name,
                            "avatar": user.avatar,
                            "role": user.role,
                            "company": user.company,
                            "timezone": user.timezone,
                        },
                    },
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                )
            )
            db.commit()
        finally:
            db.close()

        mismatched = client.post(
            "/auth/oauth/clickup/exchange",
            json={"ticket": raw_ticket},
        )
        assert mismatched.status_code == 401
        assert "provider" in mismatched.json()["detail"].lower()

        # Matching provider still works once.
        matched = client.post(
            "/auth/oauth/notion/exchange",
            json={"ticket": raw_ticket},
        )
        assert matched.status_code == 200
        assert matched.json()["accessToken"]
    finally:
        _cleanup(email)
