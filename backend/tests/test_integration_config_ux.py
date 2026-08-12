"""Google API error mapping + integration configuration UX."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.google_api_errors import raise_for_google_response
from app.integrations.google_calendar import GoogleCalendarSyncTokenExpired
from app.main import app
from app.models import Integration, RefreshToken, SyncEvent, User
from app.services.auth_service import AuthService

client = TestClient(app)


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
            name="Cfg",
            full_name="Config User",
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


def _token(user_id) -> str:
    db = SessionLocal()
    try:
        return AuthService(db).issue_tokens(db.get(User, user_id)).accessToken
    finally:
        db.close()


def _mock_response(status_code: int, payload: dict):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_calendar_access_not_configured_maps_to_conflict():
    response = _mock_response(
        403,
        {
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "Google Calendar API has not been used in project 123 before or it is disabled.",
                "errors": [{"reason": "accessNotConfigured", "domain": "usageLimits"}],
            }
        },
    )
    try:
        raise_for_google_response(response, product="Google Calendar")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
        assert "not enabled" in str(exc.detail).lower()


def test_gmail_access_not_configured_maps_to_conflict():
    response = _mock_response(
        403,
        {
            "error": {
                "message": "Gmail API has not been used in project 123 before or it is disabled.",
                "errors": [{"reason": "accessNotConfigured"}],
            }
        },
    )
    try:
        raise_for_google_response(response, product="Gmail")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
        assert "Gmail API is not enabled" in str(exc.detail)


def test_calendar_410_raises_sync_token_expired():
    response = _mock_response(410, {"error": {"message": "Sync token invalid"}})
    try:
        raise_for_google_response(
            response,
            product="Google Calendar",
            sync_token_expired_exc=GoogleCalendarSyncTokenExpired,
        )
        assert False, "expected GoogleCalendarSyncTokenExpired"
    except GoogleCalendarSyncTokenExpired:
        pass


def test_openai_and_n8n_configuration_status(monkeypatch):
    email = f"cfg-{uuid.uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-not-real")
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        token = _token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        listing = client.get("/integrations", headers=headers)
        assert listing.status_code == 200
        by_id = {i["id"]: i for i in listing.json()["integrations"]}
        assert by_id["openai"]["authType"] == "api_key"
        assert by_id["openai"]["status"] == "configured"
        assert by_id["openai"]["canConnect"] is False
        assert by_id["openai"]["canSync"] is False
        assert by_id["openai"]["canCheck"] is True
        assert "sk-test" not in listing.text
        assert by_id["n8n"]["authType"] == "webhook"
        assert by_id["n8n"]["status"] == "not-connected"
        assert "API key required" in (by_id["openai"]["statusDetail"] or "") or by_id["openai"][
            "status"
        ] == "configured"
        assert "secret" in (by_id["n8n"]["statusDetail"] or "").lower()

        openai_check = client.post("/integrations/openai/check", headers=headers)
        assert openai_check.status_code == 200
        body = openai_check.json()
        assert body["configured"] is True
        assert "sk-test" not in openai_check.text

        n8n_check = client.post("/integrations/n8n/check", headers=headers)
        assert n8n_check.status_code == 200
        assert n8n_check.json()["configured"] is False
        assert "not configured" in n8n_check.json()["message"].lower()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_google_calendar_sync_failure_sets_error_state(monkeypatch):
    email = f"sync-fail-{uuid.uuid4().hex[:8]}@example.com"
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
                    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
                    config={
                        "oauth": {
                            "access_token": encrypt_secret("ya29.x", settings),
                            "refresh_token": encrypt_secret("1//x", settings),
                            "expires_at": (
                                datetime.now(timezone.utc) + timedelta(hours=1)
                            ).isoformat(),
                        }
                    },
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        from app.services import calendar_sync_service as css
        from fastapi import HTTPException

        def _boom(self, user, *, reason="manual"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Google Calendar API is not enabled for this Google Cloud project. "
                    "Enable the Calendar API in Google Cloud Console, wait a few minutes, "
                    "then Sync again."
                ),
            )

        monkeypatch.setattr(css.CalendarSyncService, "sync_user", _boom)
        token = _token(user.id)
        response = client.post(
            "/integrations/google-calendar/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "not enabled" in response.json()["detail"].lower()

        listing = client.get(
            "/integrations",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        cal = next(i for i in listing["integrations"] if i["id"] == "google-calendar")
        assert cal["status"] == "error"
        assert cal["statusDetail"]
        assert "not enabled" in cal["statusDetail"].lower()
    finally:
        _cleanup(email)


def test_connected_never_synced_status_detail():
    email = f"never-sync-{uuid.uuid4().hex[:8]}@example.com"
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
                    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
                    config={
                        "oauth": {
                            "access_token": encrypt_secret("ya29.y", settings),
                            "refresh_token": encrypt_secret("1//y", settings),
                        }
                    },
                    connected_at=datetime.now(timezone.utc),
                    last_sync_at=None,
                )
            )
            db.commit()
        finally:
            db.close()

        token = _token(user.id)
        cal = next(
            i
            for i in client.get(
                "/integrations",
                headers={"Authorization": f"Bearer {token}"},
            ).json()["integrations"]
            if i["id"] == "google-calendar"
        )
        assert cal["status"] == "connected"
        assert cal["lastSyncLabel"] == "Never"
        assert "never synced" in (cal["statusDetail"] or "").lower()
    finally:
        _cleanup(email)
