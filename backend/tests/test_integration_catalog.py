"""Canonical integration catalog + per-user connection isolation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.main import app
from app.models import Integration, RefreshToken, SyncEvent, User
from app.services.demo_user import get_or_create_demo_user
from app.services.integration_catalog import SUPPORTED_INTEGRATIONS, catalog_ids

client = TestClient(app)

CATALOG_IDS = catalog_ids()


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        for row in db.query(Integration).filter(Integration.user_id == user.id).all():
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
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
            name="Catalog",
            full_name="Catalog User",
            role="CEO",
            company="Test",
            avatar="CU",
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


def _issue_access(user: User) -> str:
    from app.services.auth_service import AuthService

    db = SessionLocal()
    try:
        return AuthService(db).issue_tokens(db.get(User, user.id)).accessToken
    finally:
        db.close()


def _add_google_integration(user_id, *, email: str) -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        db.add(
            Integration(
                user_id=user_id,
                provider="google",
                status="connected",
                account=email,
                scopes=[
                    "openid",
                    "email",
                    "profile",
                    "calendar.readonly",
                    "gmail.readonly",
                ],
                config={
                    "name": "Google",
                    "oauth": {
                        "access_token": encrypt_secret("ya29.secret-token", settings),
                        "refresh_token": encrypt_secret("1//secret-refresh", settings),
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                    },
                    "profile": {"sub": "google-sub-1", "email": email},
                },
                last_sync_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                connected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()


def test_new_google_user_sees_complete_catalog_with_only_google_connected():
    email = f"catalog-google-{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        user = _seed_user(email)
        _add_google_integration(user.id, email=email)
        token = _issue_access(user)

        response = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        ids = {i["id"] for i in data["integrations"]}
        assert CATALOG_IDS.issubset(ids)
        assert data["totalCount"] >= len(SUPPORTED_INTEGRATIONS)

        by_id = {i["id"]: i for i in data["integrations"]}
        assert by_id["google-calendar"]["status"] == "connected"
        assert by_id["gmail"]["status"] == "connected"
        assert by_id["google-calendar"]["account"] == email
        assert by_id["gmail"]["account"] == email
        assert by_id["google-calendar"]["lastSyncLabel"] != "Never"
        assert by_id["gmail"]["lastSyncLabel"] != "Never"

        for provider_id in (
            "notion",
            "gohighlevel",
            "monday",
            "clickup",
        ):
            assert by_id[provider_id]["status"] == "not-connected"
            assert by_id[provider_id]["account"] is None
            assert by_id[provider_id]["lastSync"] is None
            assert by_id[provider_id]["lastSyncLabel"] == "Never"

        # OpenAI / n8n are env-configured — never OAuth; never expose secrets.
        assert by_id["openai"]["authType"] == "api_key"
        assert by_id["openai"]["canConnect"] is False
        assert by_id["n8n"]["authType"] == "webhook"
        assert by_id["n8n"]["canConnect"] is False
        # No OAuth secrets / API keys / webhook secrets in the payload.
        assert "ya29." not in response.text
        assert "sk-" not in response.text
        assert "access_token" not in response.text
        assert "refresh_token" not in response.text

        # No OAuth secrets leak into the Integrations payload.
        payload = response.text
        assert "ya29.secret-token" not in payload
        assert "1//secret-refresh" not in payload
        assert "access_token" not in payload
    finally:
        _cleanup(email)


def test_connected_google_oauth_preferred_over_stale_calendar_alias():
    """provider=google is the credential source; prefer it over a leftover alias row."""
    email = f"catalog-prefer-{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="google-calendar",
                    status="connected",
                    account="stale-demo@example.com",
                    scopes=["calendar.readonly"],
                    config={"name": "Google Calendar"},
                    last_sync_at=datetime.now(timezone.utc) - timedelta(days=30),
                    connected_at=datetime.now(timezone.utc) - timedelta(days=30),
                )
            )
            db.add(
                Integration(
                    user_id=user.id,
                    provider="google",
                    status="connected",
                    account=email,
                    scopes=["openid", "email", "profile", "calendar.readonly", "gmail.readonly"],
                    config={
                        "name": "Google",
                        "oauth": {
                            "access_token": encrypt_secret("ya29.prefer", settings),
                            "refresh_token": encrypt_secret("1//prefer", settings),
                        },
                        "profile": {"sub": "prefer-sub", "email": email},
                    },
                    last_sync_at=datetime.now(timezone.utc),
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        token = _issue_access(user)
        response = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
        by_id = {i["id"]: i for i in response.json()["integrations"]}
        assert by_id["google-calendar"]["account"] == email
        assert by_id["gmail"]["account"] == email
        assert by_id["google-calendar"]["status"] == "connected"
    finally:
        _cleanup(email)


def test_another_users_integration_never_appears():
    owner_email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer-{uuid.uuid4().hex[:8]}@example.com"
    try:
        owner = _seed_user(owner_email)
        viewer = _seed_user(viewer_email)

        db = SessionLocal()
        try:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=owner.id,
                    provider="notion",
                    status="connected",
                    account="Owner Workspace",
                    scopes=["read_content"],
                    config={
                        "name": "Notion",
                        "oauth": {
                            "access_token": encrypt_secret("owner-notion-token", settings),
                        },
                    },
                    last_sync_at=datetime.now(timezone.utc),
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        token = _issue_access(viewer)
        response = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        by_id = {i["id"]: i for i in response.json()["integrations"]}
        assert by_id["notion"]["status"] == "not-connected"
        assert by_id["notion"]["account"] is None
        assert "Owner Workspace" not in response.text
        assert "owner-notion-token" not in response.text
    finally:
        _cleanup(owner_email)
        _cleanup(viewer_email)


def test_demo_user_seeded_integrations_remain_connected():
    db = SessionLocal()
    try:
        demo = get_or_create_demo_user(db)
        # Ensure at least one seeded connected OAuth provider exists for the demo tenant.
        existing = (
            db.query(Integration)
            .filter(Integration.user_id == demo.id, Integration.provider == "notion")
            .first()
        )
        if existing is None:
            db.add(
                Integration(
                    user_id=demo.id,
                    provider="notion",
                    status="connected",
                    account="Arcadia Workspace",
                    scopes=["read_content"],
                    config={
                        "name": "Notion",
                        "category": "Knowledge",
                        "description": "Plans",
                        "metrics": [{"label": "Pages indexed", "value": "12"}],
                        "poweredBy": "Notion API",
                    },
                    last_sync_at=datetime.now(timezone.utc),
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
    finally:
        db.close()

    # Default AUTH_REQUIRED=false → demo user without Bearer.
    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()
    ids = {i["id"] for i in data["integrations"]}
    assert CATALOG_IDS.issubset(ids)
    notion = next(i for i in data["integrations"] if i["id"] == "notion")
    assert notion["status"] in ("connected", "syncing")
    openai = next(i for i in data["integrations"] if i["id"] == "openai")
    assert openai["authType"] == "api_key"
    assert openai["status"] in ("configured", "not-connected")
    assert openai["canConnect"] is False


def test_disconnected_providers_expose_oauth_ready_catalog_entries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    email = f"oauth-ready-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        token = _issue_access(user)
        response = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
        by_id = {i["id"]: i for i in response.json()["integrations"]}
        for provider_id in ("google-calendar", "gmail", "notion", "gohighlevel", "monday", "clickup"):
            assert by_id[provider_id]["status"] == "not-connected"
            assert by_id[provider_id]["id"] == provider_id
            assert by_id[provider_id]["canConnect"] is True
        # Config-only providers remain visible but not OAuth-connectable.
        assert by_id["openai"]["status"] == "not-connected"
        assert by_id["openai"]["canConnect"] is False
        assert by_id["n8n"]["status"] == "not-connected"
        assert by_id["n8n"]["canConnect"] is False
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_connection_metadata_only_from_current_user_rows():
    email = f"meta-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        sync_at = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
        db = SessionLocal()
        try:
            db.add(
                Integration(
                    user_id=user.id,
                    provider="monday",
                    status="connected",
                    account="My monday account",
                    scopes=["boards:read"],
                    config={"name": "monday.com"},
                    last_sync_at=sync_at,
                    connected_at=sync_at,
                )
            )
            db.commit()
        finally:
            db.close()

        token = _issue_access(user)
        response = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        )
        monday = next(i for i in response.json()["integrations"] if i["id"] == "monday")
        assert monday["status"] == "connected"
        assert monday["account"] == "My monday account"
        assert monday["lastSync"] == sync_at.isoformat()
        assert monday["lastSyncLabel"] != "Never"

        gmail = next(i for i in response.json()["integrations"] if i["id"] == "gmail")
        assert gmail["status"] == "not-connected"
        assert gmail["lastSync"] is None
    finally:
        _cleanup(email)
