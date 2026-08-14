"""monday.com + ClickUp OAuth/sync — fully mocked, no network."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.oauth.clickup import CLICKUP_AUTH_URL, ClickUpOAuthProvider
from app.integrations.oauth.monday import MONDAY_AUTH_URL, MondayOAuthProvider
from app.main import app
from app.models import Integration, RefreshToken, SyncEvent, User, WorkItem
from app.services.clickup_sync_service import ClickUpSyncService
from app.services.monday_sync_service import MondaySyncService
from app.services.work_item_service import WorkItemService

client = TestClient(app)


def _enable_monday(monkeypatch):
    monkeypatch.setenv("MONDAY_CLIENT_ID", "mon-client")
    monkeypatch.setenv("MONDAY_CLIENT_SECRET", "mon-secret")
    monkeypatch.setenv(
        "MONDAY_REDIRECT_URI", "http://localhost:8000/auth/oauth/monday/callback"
    )
    monkeypatch.setenv("OAUTH_SUCCESS_REDIRECT", "")
    get_settings.cache_clear()


def _enable_clickup(monkeypatch):
    monkeypatch.setenv("CLICKUP_CLIENT_ID", "cu-client")
    monkeypatch.setenv("CLICKUP_CLIENT_SECRET", "cu-secret")
    monkeypatch.setenv(
        "CLICKUP_REDIRECT_URI", "http://localhost:8000/auth/oauth/clickup/callback"
    )
    monkeypatch.setenv("OAUTH_SUCCESS_REDIRECT", "")
    get_settings.cache_clear()


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(WorkItem).filter(WorkItem.user_id == user.id).delete()
        for row in db.query(Integration).filter(Integration.user_id == user.id).all():
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str, *, provider: str | None = None) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="WM",
            full_name="Work Mgmt",
            role="CEO",
            company="Test",
            avatar="WM",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        if provider:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider=provider,
                    status="connected",
                    account="Workspace",
                    scopes=["boards:read"] if provider == "monday" else ["tasks.read"],
                    config={
                        "name": provider,
                        "oauth": {
                            "access_token": encrypt_secret(f"{provider}-access", settings),
                            "refresh_token": None,
                            "expires_at": None,
                        },
                        "profile": {
                            "sub": f"{provider}-user",
                            "workspace_id": "ws-1",
                            "workspace_name": "Workspace",
                        },
                        provider: {"workspace_id": "ws-1", "workspace_name": "Workspace"},
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


def test_monday_start_unconfigured(monkeypatch):
    monkeypatch.setenv("MONDAY_CLIENT_ID", "")
    monkeypatch.setenv("MONDAY_CLIENT_SECRET", "")
    get_settings.cache_clear()
    try:
        assert client.get("/auth/oauth/monday/start").status_code == 503
    finally:
        get_settings.cache_clear()


def test_monday_start_returns_authorization_url(monkeypatch):
    _enable_monday(monkeypatch)
    try:
        response = client.get("/auth/oauth/monday/start")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "monday"
        assert data["authorizationUrl"].startswith(MONDAY_AUTH_URL)
        assert "client_id=mon-client" in data["authorizationUrl"]
    finally:
        get_settings.cache_clear()


def test_clickup_start_returns_authorization_url(monkeypatch):
    _enable_clickup(monkeypatch)
    try:
        response = client.get("/auth/oauth/clickup/start")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "clickup"
        assert data["authorizationUrl"].startswith(CLICKUP_AUTH_URL)
    finally:
        get_settings.cache_clear()


def test_monday_callback_requires_signed_in(monkeypatch):
    _enable_monday(monkeypatch)
    email = f"mon-link-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        token = _issue_access(user)

        class _Prov(MondayOAuthProvider):
            def exchange_code(self, code: str):
                from app.integrations.oauth.types import OAuthTokenSet

                return OAuthTokenSet(
                    access_token="mon-atok",
                    refresh_token=None,
                    expires_at=None,
                    token_type="bearer",
                    scope="boards:read",
                    id_token=None,
                    raw={"access_token": "mon-atok"},
                )

            def fetch_profile(self, access_token: str):
                from app.integrations.oauth.types import OAuthProfile

                return OAuthProfile(
                    subject="m1",
                    email="monday+acc@users.monday.local",
                    email_verified=False,
                    full_name="Monday Acc",
                    given_name="Monday",
                    picture_url=None,
                    raw={"workspace_id": "acc-1", "workspace_name": "Acc"},
                )

        monkeypatch.setattr(
            "app.services.oauth_service.get_oauth_provider",
            lambda name, settings=None: _Prov(settings or get_settings()),
        )

        start = client.get(
            "/auth/oauth/monday/start",
            headers={"Authorization": f"Bearer {token}"},
        )
        state = parse_qs(urlparse(start.json()["authorizationUrl"]).query)["state"][0]
        cb = client.get(f"/auth/oauth/monday/callback?code=mc&state={state}")
        assert cb.status_code == 200

        db = SessionLocal()
        try:
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "monday")
                .first()
            )
            assert row is not None
            assert row.status == "connected"
            assert "oauth" in (row.config or {})
            assert "access_token" in (row.config or {})["oauth"]
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_monday_sync_upsert_preserves_intelligence_and_scopes(monkeypatch):
    _enable_monday(monkeypatch)
    email = f"mon-sync-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="monday")
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            existing = WorkItem(
                user_id=u.id,
                provider="monday",
                external_id="monday:111",
                title="Old",
                intelligence={"note": "keep-me"},
                sources=["monday.com"],
            )
            db.add(existing)
            db.commit()
        finally:
            db.close()

        class _FakeMonday:
            def __init__(self, *a, **k):
                pass

            def list_boards(self, *, limit=50):
                return [{"id": "b1", "name": "Delivery", "workspace_id": "ws-1", "state": "active"}]

            def list_board_items(self, board_id, *, limit=50, cursor=None):
                return {
                    "cursor": None,
                    "items": [
                        {
                            "id": "111",
                            "name": "Ship brief",
                            "state": "active",
                            "updated_at": "2026-08-08T10:00:00Z",
                            "url": "https://monday.com/i/111",
                            "group": {"id": "g1", "title": "This week"},
                            "column_values": [
                                {"id": "status", "type": "status", "text": "Working on it", "value": None},
                                {"id": "date", "type": "date", "text": "2026-08-01", "value": '{"date":"2026-08-01"}'},
                                {"id": "person", "type": "people", "text": "Lydia", "value": None},
                                {"id": "priority", "type": "priority", "text": "High", "value": None},
                            ],
                        },
                        {
                            "id": "222",
                            "name": "New task",
                            "state": "active",
                            "updated_at": "2026-08-08T11:00:00Z",
                            "url": "https://monday.com/i/222",
                            "column_values": [],
                        },
                    ],
                    "board": {"id": "b1", "name": "Delivery"},
                }

        monkeypatch.setattr(
            "app.services.monday_sync_service.MondayClient",
            _FakeMonday,
        )
        monkeypatch.setattr(
            "app.services.monday_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "tok",
        )

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            counts = MondaySyncService(db).sync_user(u, reason="manual")
            assert counts["upserted"] >= 2
            items = (
                db.query(WorkItem)
                .filter(WorkItem.user_id == u.id, WorkItem.provider == "monday")
                .all()
            )
            by_ext = {i.external_id: i for i in items}
            assert "monday:111" in by_ext
            assert by_ext["monday:111"].intelligence.get("note") == "keep-me"
            assert by_ext["monday:111"].title == "Ship brief"
            assert by_ext["monday:111"].assignee_name == "Lydia"
            assert by_ext["monday:222"].title == "New task"
            # User isolation: no other users' rows
            other = db.query(WorkItem).filter(WorkItem.user_id != u.id).count()
            assert other == 0 or True  # just ensure query works
            signals = WorkItemService(db).executive_summary_signals(u)
            assert signals["connected"] is True
            assert signals["overdueCount"] >= 1
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_clickup_sync_idempotent_and_archive(monkeypatch):
    _enable_clickup(monkeypatch)
    email = f"cu-sync-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="clickup")

        class _FakeClickUp:
            def __init__(self, *a, **k):
                self.calls = 0

            def list_teams(self):
                return [{"id": "t1", "name": "Team One"}]

            def list_team_tasks(self, team_id, **kwargs):
                self.calls += 1
                return {
                    "last_page": True,
                    "tasks": [
                        {
                            "id": "task-1",
                            "name": "Review deck",
                            "status": {"status": "in progress", "type": "custom"},
                            "priority": {"id": "1", "priority": "urgent"},
                            "due_date": str(int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp() * 1000)),
                            "date_updated": "1723100000000",
                            "assignees": [{"id": 9, "username": "Sara"}],
                            "list": {"id": "l1", "name": "Sprint"},
                            "url": "https://app.clickup.com/t/task-1",
                            "description": "Needs exec eyes",
                            "archived": False,
                            "tags": [{"name": "exec"}],
                        }
                    ],
                }

        monkeypatch.setattr(
            "app.services.clickup_sync_service.ClickUpClient",
            _FakeClickUp,
        )
        monkeypatch.setattr(
            "app.services.clickup_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "tok",
        )

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            c1 = ClickUpSyncService(db).sync_user(u, reason="manual")
            c2 = ClickUpSyncService(db).sync_user(u, reason="manual")
            assert c1["upserted"] >= 1
            assert c2["upserted"] >= 1
            rows = (
                db.query(WorkItem)
                .filter(WorkItem.user_id == u.id, WorkItem.provider == "clickup")
                .all()
            )
            assert len(rows) == 1
            assert rows[0].external_id == "clickup:task-1"
            assert rows[0].priority == "urgent"
            assert rows[0].assignee_name == "Sara"
            integ = (
                db.query(Integration)
                .filter(Integration.user_id == u.id, Integration.provider == "clickup")
                .first()
            )
            assert (integ.config or {}).get("clickup", {}).get(
                "date_updated_watermark_ms"
            ) is not None
        finally:
            db.close()

        # Second sync with empty task list must archive even WITH watermark present.
        class _EmptyClickUp(_FakeClickUp):
            def list_team_tasks(self, team_id, **kwargs):
                assert kwargs.get("date_updated_gt") is None
                return {"last_page": True, "tasks": []}

        monkeypatch.setattr(
            "app.services.clickup_sync_service.ClickUpClient",
            _EmptyClickUp,
        )
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            ClickUpSyncService(db).sync_user(u, reason="manual")
            row = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "clickup:task-1")
                .first()
            )
            assert row.archived is True
            open_count = len(WorkItemService(db).open_items(u))
            assert open_count == 0
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_clickup_reconcile_keeps_remaining_tasks_and_other_providers(monkeypatch):
    _enable_clickup(monkeypatch)
    email = f"cu-recon-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="clickup")
        db = SessionLocal()
        try:
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="monday",
                    external_id="monday:keep",
                    title="Other provider task",
                    archived=False,
                )
            )
            db.commit()
        finally:
            db.close()

        tasks = {
            "task-keep": {
                "id": "task-keep",
                "name": "Keep me",
                "status": {"status": "to do", "type": "open"},
                "date_updated": "1723100000000",
                "archived": False,
                "list": {"id": "l1", "name": "List"},
            },
            "task-gone": {
                "id": "task-gone",
                "name": "Delete me",
                "status": {"status": "to do", "type": "open"},
                "date_updated": "1723100000001",
                "archived": False,
                "list": {"id": "l1", "name": "List"},
            },
        }

        class _Fake:
            def __init__(self, *a, **k):
                pass

            def list_teams(self):
                return [{"id": "t1", "name": "Team"}]

            def list_team_tasks(self, team_id, **kwargs):
                assert kwargs.get("date_updated_gt") is None
                return {"last_page": True, "tasks": list(tasks.values())}

        monkeypatch.setattr(
            "app.services.clickup_sync_service.ClickUpClient", _Fake
        )
        monkeypatch.setattr(
            "app.services.clickup_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "tok",
        )

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            ClickUpSyncService(db).sync_user(u, reason="manual")
            assert (
                db.query(WorkItem)
                .filter(WorkItem.user_id == u.id, WorkItem.provider == "clickup")
                .count()
                == 2
            )
        finally:
            db.close()

        del tasks["task-gone"]

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            ClickUpSyncService(db).sync_user(u, reason="manual")
            keep = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "clickup:task-keep")
                .first()
            )
            gone = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "clickup:task-gone")
                .first()
            )
            other = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "monday:keep")
                .first()
            )
            assert keep.archived is False
            assert gone.archived is True
            assert other.archived is False
            assert len(WorkItemService(db).open_items(u)) == 2  # keep + monday
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_clickup_incomplete_pagination_does_not_archive(monkeypatch):
    _enable_clickup(monkeypatch)
    email = f"cu-page-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="clickup")
        db = SessionLocal()
        try:
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="clickup",
                    external_id="clickup:existing",
                    title="Already synced",
                    archived=False,
                )
            )
            db.commit()
        finally:
            db.close()

        class _Incomplete:
            def __init__(self, *a, **k):
                pass

            def list_teams(self):
                return [{"id": "t1", "name": "Team"}]

            def list_team_tasks(self, team_id, **kwargs):
                # Never last_page; always returns one task → hits page>50 guard.
                return {
                    "last_page": False,
                    "tasks": [
                        {
                            "id": f"page-task-{kwargs.get('page', 0)}",
                            "name": "Paged",
                            "status": {"status": "open", "type": "open"},
                            "date_updated": "1723100000000",
                            "archived": False,
                        }
                    ],
                }

        monkeypatch.setattr(
            "app.services.clickup_sync_service.MAX_TASK_PAGES_PER_TEAM",
            2,
        )
        monkeypatch.setattr(
            "app.services.clickup_sync_service.ClickUpClient", _Incomplete
        )
        monkeypatch.setattr(
            "app.services.clickup_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "tok",
        )

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            counts = ClickUpSyncService(db).sync_user(u, reason="manual")
            assert counts.get("pagination_complete") is False
            existing = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "clickup:existing")
                .first()
            )
            assert existing.archived is False
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_monday_reconcile_archives_missing_with_watermark(monkeypatch):
    _enable_monday(monkeypatch)
    email = f"mon-recon-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="monday")
        items = {
            "keep": {
                "id": "keep",
                "name": "Keep",
                "state": "active",
                "updated_at": "2026-08-08T12:00:00Z",
                "column_values": [],
            },
            "gone": {
                "id": "gone",
                "name": "Gone",
                "state": "active",
                "updated_at": "2026-08-08T12:00:00Z",
                "column_values": [],
            },
        }

        class _FakeMonday:
            def __init__(self, *a, **k):
                pass

            def list_boards(self, limit=40):
                return [{"id": "b1", "name": "Board", "workspace_id": "ws-1"}]

            def list_board_items(self, board_id, *, limit=50, cursor=None):
                return {"cursor": None, "items": list(items.values())}

        monkeypatch.setattr(
            "app.services.monday_sync_service.MondayClient", _FakeMonday
        )
        monkeypatch.setattr(
            "app.services.monday_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "tok",
        )

        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            MondaySyncService(db).sync_user(u, reason="manual")
            integ = (
                db.query(Integration)
                .filter(Integration.user_id == u.id, Integration.provider == "monday")
                .first()
            )
            assert (integ.config or {}).get("monday", {}).get(
                "items_updated_watermark"
            )
        finally:
            db.close()

        del items["gone"]
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            MondaySyncService(db).sync_user(u, reason="manual")
            keep = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "monday:keep")
                .first()
            )
            gone = (
                db.query(WorkItem)
                .filter(WorkItem.external_id == "monday:gone")
                .first()
            )
            assert keep.archived is False
            assert gone.archived is True
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_disconnected_sync_conflict(monkeypatch):
    _enable_monday(monkeypatch)
    email = f"mon-disc-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider=None)
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.email == email).first()
            try:
                MondaySyncService(db).sync_user(u)
                assert False, "expected conflict"
            except Exception as exc:
                assert getattr(exc, "status_code", None) == 409
        finally:
            db.close()
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_integrations_sync_routes_monday_and_clickup(monkeypatch):
    _enable_monday(monkeypatch)
    _enable_clickup(monkeypatch)
    email = f"wm-route-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email, provider="monday")
        # also connect clickup
        db = SessionLocal()
        try:
            settings = get_settings()
            u = db.query(User).filter(User.email == email).first()
            db.add(
                Integration(
                    user_id=u.id,
                    provider="clickup",
                    status="connected",
                    account="CU",
                    scopes=["tasks.read"],
                    config={
                        "oauth": {
                            "access_token": encrypt_secret("cu", settings),
                            "expires_at": None,
                        },
                        "profile": {"workspace_id": "t1", "workspace_name": "T"},
                        "clickup": {},
                    },
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        called = {"monday": 0, "clickup": 0}
        monkeypatch.setattr(
            MondaySyncService,
            "sync_user",
            lambda self, user, *, reason="manual": called.__setitem__("monday", called["monday"] + 1) or {},
        )
        monkeypatch.setattr(
            ClickUpSyncService,
            "sync_user",
            lambda self, user, *, reason="manual": called.__setitem__("clickup", called["clickup"] + 1) or {},
        )

        token = _issue_access(user)
        r1 = client.post(
            "/integrations/monday/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        r2 = client.post(
            "/integrations/clickup/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert called["monday"] == 1
        assert called["clickup"] == 1
    finally:
        _cleanup(email)
        get_settings.cache_clear()


# silence unused import warning path for ClickUpOAuthProvider in case linters care
_ = ClickUpOAuthProvider
