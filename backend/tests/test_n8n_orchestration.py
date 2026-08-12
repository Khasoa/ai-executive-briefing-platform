"""n8n webhook authentication + orchestration (mocked provider syncs)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models import Integration, Opportunity, RefreshToken, User
from app.services.calendar_sync_service import CalendarSyncService
from app.services.ghl_sync_service import GHLSyncService
from app.services.gmail_sync_service import GmailSyncService
from app.services.notion_sync_service import NotionSyncService

client = TestClient(app)
SECRET = "test-n8n-secret-please-rotate"


def _enable_secret(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", SECRET)
    get_settings.cache_clear()


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(Opportunity).filter(Opportunity.user_id == user.id).delete()
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
            email=email,
            hashed_password=None,
            name="Orch",
            full_name="Orch User",
            role="CEO",
            company="Test",
            avatar="OU",
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


def test_n8n_rejects_missing_secret(monkeypatch):
    _enable_secret(monkeypatch)
    try:
        response = client.post("/webhooks/n8n/run", json={})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_n8n_rejects_wrong_secret(monkeypatch):
    _enable_secret(monkeypatch)
    try:
        response = client.post(
            "/webhooks/n8n/run",
            json={},
            headers={"X-Briefly-N8N-Secret": "wrong"},
        )
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_n8n_unavailable_when_unconfigured(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/webhooks/n8n/run",
            json={},
            headers={"X-Briefly-N8N-Secret": "anything"},
        )
        assert response.status_code == 503
    finally:
        get_settings.cache_clear()


def test_n8n_run_partial_failure_continues(monkeypatch):
    _enable_secret(monkeypatch)
    email = f"n8n-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)

        def gmail_fail(self, u, *, reason="n8n"):
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="Gmail unavailable")

        def cal_ok(self, u, *, reason="n8n"):
            return {"upserted": 1, "deleted": 0, "pages": 1}

        def notion_skip(self, u, *, reason="n8n"):
            from fastapi import HTTPException

            raise HTTPException(status_code=409, detail="Notion is not connected")

        def ghl_ok(self, u, *, reason="n8n"):
            return {"upserted": 2, "closed": 0, "pages": 1}

        monkeypatch.setattr(GmailSyncService, "sync_user", gmail_fail)
        monkeypatch.setattr(CalendarSyncService, "sync_user", cal_ok)
        monkeypatch.setattr(NotionSyncService, "sync_user", notion_skip)
        monkeypatch.setattr(GHLSyncService, "sync_user", ghl_ok)

        response = client.post(
            "/webhooks/n8n/run",
            headers={"X-Briefly-N8N-Secret": SECRET},
            json={
                "userEmail": email,
                "providers": ["google-calendar", "gmail", "notion", "gohighlevel"],
                "regenerateMorningBrief": False,
                "regenerateWeeklyDigest": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["partial"] is True
        by_provider = {s["provider"]: s for s in body["steps"]}
        assert by_provider["google-calendar"]["status"] == "success"
        assert by_provider["gmail"]["status"] == "error"
        assert by_provider["notion"]["status"] == "skipped"
        assert by_provider["gohighlevel"]["status"] == "success"
        assert body["userEmail"] == email
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_n8n_daily_success(monkeypatch):
    _enable_secret(monkeypatch)
    email = f"n8n-daily-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)

        monkeypatch.setattr(
            CalendarSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            GmailSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            NotionSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            GHLSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )

        from app.services.morning_brief_service import MorningBriefService

        class _Meta:
            headline = "Daily stub"

        class _Brief:
            meta = _Meta()

        monkeypatch.setattr(
            MorningBriefService, "regenerate", lambda self: _Brief()
        )

        response = client.post(
            "/webhooks/n8n/daily",
            headers={"X-Briefly-N8N-Secret": SECRET},
            json={"userEmail": email},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["error"] == 0
        assert any(s["provider"] == "morning-brief" for s in body["steps"])
        assert body["ok"] is True
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_n8n_weekly_regenerates_digest(monkeypatch):
    _enable_secret(monkeypatch)
    email = f"n8n-weekly-{uuid.uuid4().hex[:8]}@example.com"
    try:
        _seed_user(email)
        monkeypatch.setattr(
            CalendarSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            GmailSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            NotionSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )
        monkeypatch.setattr(
            GHLSyncService, "sync_user", lambda self, u, *, reason="n8n": {}
        )

        from app.services.weekly_digest_service import WeeklyDigestService

        class _Digest:
            headline = "Weekly stub"

        monkeypatch.setattr(
            WeeklyDigestService, "regenerate", lambda self: _Digest()
        )

        response = client.post(
            "/webhooks/n8n/weekly",
            headers={"X-Briefly-N8N-Secret": SECRET},
            json={"userEmail": email},
        )
        assert response.status_code == 200
        body = response.json()
        assert any(s["provider"] == "weekly-digest" for s in body["steps"])
        assert body["ok"] is True
    finally:
        _cleanup(email)
        get_settings.cache_clear()
