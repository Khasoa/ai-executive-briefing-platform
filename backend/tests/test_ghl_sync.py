"""GoHighLevel OAuth + opportunity sync — fully mocked, no network."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.oauth.gohighlevel import GHL_AUTH_URL, GoHighLevelOAuthProvider
from app.main import app
from app.models import Integration, Opportunity, RefreshToken, SyncEvent, User
from app.services.ghl_sync_service import GHLSyncService

client = TestClient(app)


def _settings(**overrides):
    get_settings.cache_clear()
    base = {
        "GHL_CLIENT_ID": "test-ghl-client",
        "GHL_CLIENT_SECRET": "test-ghl-secret",
        "GHL_REDIRECT_URI": "http://localhost:8000/auth/oauth/gohighlevel/callback",
        "OAUTH_SUCCESS_REDIRECT": "",
    }
    base.update(overrides)
    return base


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(Opportunity).filter(Opportunity.user_id == user.id).delete()
        for row in db.query(Integration).filter(Integration.user_id == user.id).all():
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str, *, with_ghl: bool = True) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="GHL",
            full_name="GHL User",
            role="CEO",
            company="Test",
            avatar="GU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        if with_ghl:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="gohighlevel",
                    status="connected",
                    account="Location loc-1",
                    scopes=["opportunities.readonly"],
                    config={
                        "name": "GoHighLevel",
                        "oauth": {
                            "access_token": encrypt_secret("ghl-access", settings),
                            "refresh_token": encrypt_secret("ghl-refresh", settings),
                            "expires_at": (
                                datetime.now(timezone.utc) + timedelta(hours=2)
                            ).isoformat(),
                        },
                        "profile": {"sub": "ghl-user-1", "location_id": "loc-1"},
                        "ghl": {"location_id": "loc-1"},
                    },
                    connected_at=datetime.now(timezone.utc),
                )
            )
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


class _FakeGHL:
    def __init__(self, opportunities=None, pipelines=None):
        self.opportunities = opportunities or []
        self.pipelines = pipelines or [
            {
                "id": "pipe-1",
                "stages": [{"id": "stage-1", "name": "Negotiation"}],
            }
        ]

    def list_pipelines(self, location_id):
        return self.pipelines

    def search_opportunities(self, *, location_id, status=None, limit=100, skip=0):
        rows = [
            o
            for o in self.opportunities
            if (status is None or (o.get("status") or "open") == status)
        ]
        return {"opportunities": rows[skip : skip + limit]}


def test_ghl_start_requires_configuration(monkeypatch):
    monkeypatch.setenv("GHL_CLIENT_ID", "")
    monkeypatch.setenv("GHL_CLIENT_SECRET", "")
    get_settings.cache_clear()
    try:
        assert client.get("/auth/oauth/gohighlevel/start").status_code == 503
    finally:
        get_settings.cache_clear()


def test_ghl_start_returns_authorization_url(monkeypatch):
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        response = client.get("/auth/oauth/gohighlevel/start")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "gohighlevel"
        assert data["authorizationUrl"].startswith(GHL_AUTH_URL)
        params = parse_qs(urlparse(data["authorizationUrl"]).query)
        assert params["client_id"] == ["test-ghl-client"]
        assert "opportunities.readonly" in params["scope"][0]
    finally:
        get_settings.cache_clear()


def test_ghl_callback_links_signed_in_user(monkeypatch):
    email = f"ghl-owner-{uuid.uuid4().hex[:8]}@example.com"
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        user = _seed_user(email, with_ghl=False)
        start = client.get(
            "/auth/oauth/gohighlevel/start",
            headers={"Authorization": f"Bearer {_issue_access(user)}"},
        )
        state = start.json()["state"]

        from app.integrations.oauth import types as oauth_types

        token_set = oauth_types.OAuthTokenSet(
            access_token="ghl-access-new",
            refresh_token="ghl-refresh-new",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            raw={"locationId": "loc-99", "userId": "user-99"},
        )
        monkeypatch.setattr(
            GoHighLevelOAuthProvider, "exchange_code", lambda self, code: token_set
        )

        response = client.get(
            f"/auth/oauth/gohighlevel/callback?code=ghl-code&state={state}"
        )
        assert response.status_code == 200
        assert response.json()["user"]["email"] == email

        db = SessionLocal()
        try:
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "gohighlevel")
                .one()
            )
            assert row.status == "connected"
            assert row.config["ghl"]["location_id"] == "loc-99"
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_ghl_sync_upserts_preserves_ai_and_scopes_user(monkeypatch):
    email = f"ghl-sync-{uuid.uuid4().hex[:8]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        opp = {
            "id": "opp-1",
            "name": "Meridian Renewal",
            "monetaryValue": 480000,
            "pipelineStageId": "stage-1",
            "status": "open",
            "assignedTo": "Elena Park",
            "expectedCloseDate": "2026-08-15",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "contact": {"companyName": "Meridian Labs", "name": "James Liu"},
            "locationId": "loc-1",
        }
        fake = _FakeGHL(opportunities=[opp])
        monkeypatch.setattr(
            "app.services.ghl_sync_service.GHLClient",
            lambda token, settings=None: fake,
        )

        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            db.add(
                Opportunity(
                    user_id=u.id,
                    external_id="ghl:opp-1",
                    company="Old Name",
                    stage="Old",
                    value=1,
                    probability=10,
                    owner="X",
                    risk_level="critical",
                    ai_summary="Keep this AI summary",
                    recommended_action="Call champion",
                    signals=["silence"],
                    last_interaction={"sources": ["OpenAI"]},
                )
            )
            db.commit()

            counts = GHLSyncService(db).sync_user(u, reason="manual")
            assert counts["upserted"] >= 1
            row = (
                db.query(Opportunity)
                .filter(Opportunity.user_id == u.id, Opportunity.external_id == "ghl:opp-1")
                .one()
            )
            assert row.company == "Meridian Labs"
            assert row.stage == "Negotiation"
            assert row.ai_summary == "Keep this AI summary"
            assert row.recommended_action == "Call champion"
            assert row.risk_level == "critical"
            assert "GoHighLevel" in (row.last_interaction or {}).get("sources", [])
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_ghl_sync_marks_missing_open_deals_closed(monkeypatch):
    email = f"ghl-close-{uuid.uuid4().hex[:8]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        fake = _FakeGHL(opportunities=[])
        monkeypatch.setattr(
            "app.services.ghl_sync_service.GHLClient",
            lambda token, settings=None: fake,
        )
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            db.add(
                Opportunity(
                    user_id=u.id,
                    external_id="ghl:gone",
                    company="Vanished Co",
                    stage="Proposal",
                    value=10000,
                    probability=40,
                    owner="A",
                    last_interaction={"ghl": {"status": "open"}, "sources": ["GoHighLevel"]},
                )
            )
            db.commit()
            counts = GHLSyncService(db).sync_user(u)
            assert counts["closed"] >= 1
            row = (
                db.query(Opportunity)
                .filter(Opportunity.external_id == "ghl:gone")
                .one()
            )
            assert "closed" in row.stage.lower()
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_ghl_sync_conflict_when_disconnected():
    email = f"ghl-off-{uuid.uuid4().hex[:8]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email, with_ghl=False)
        db = SessionLocal()
        try:
            from fastapi import HTTPException

            try:
                GHLSyncService(db).sync_user(db.get(User, user.id))
                assert False
            except HTTPException as exc:
                assert exc.status_code == 409
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_integrations_sync_triggers_ghl(monkeypatch):
    email = f"ghl-api-{uuid.uuid4().hex[:8]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        called = {"ok": False}

        def _fake(self, u, *, reason="manual"):
            called["ok"] = True
            return {"upserted": 0, "closed": 0, "pages": 0}

        monkeypatch.setattr(GHLSyncService, "sync_user", _fake)
        token = _issue_access(user)
        response = client.post(
            "/integrations/gohighlevel/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert called["ok"] is True
    finally:
        _cleanup(email)
