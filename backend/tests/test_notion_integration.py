"""Notion OAuth + incremental sync — fully mocked, no network."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.oauth.notion import NOTION_AUTH_URL, NotionOAuthProvider
from app.main import app
from app.models import (
    Integration,
    NotionItem,
    OAuthLoginTicket,
    OAuthState,
    RefreshToken,
    SyncEvent,
    User,
)
from app.services.ai_service import AIService
from app.services.notion_sync_service import NotionSyncService
from app.services.overview_service import OverviewService

client = TestClient(app)


def _settings(**overrides):
    get_settings.cache_clear()
    base = {
        "NOTION_CLIENT_ID": "test-notion-client-id",
        "NOTION_CLIENT_SECRET": "test-notion-client-secret",
        "NOTION_REDIRECT_URI": "http://localhost:8000/auth/oauth/notion/callback",
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
        db.query(NotionItem).filter(NotionItem.user_id == user.id).delete()
        integrations = db.query(Integration).filter(Integration.user_id == user.id).all()
        for row in integrations:
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.query(OAuthLoginTicket).filter(OAuthLoginTicket.user_id == user.id).delete()
        db.query(OAuthState).filter(OAuthState.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str, *, with_notion: bool = True) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="Notion",
            full_name="Notion User",
            role="CEO",
            company="Test",
            avatar="NU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if with_notion:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="notion",
                    status="connected",
                    account="Test Workspace",
                    scopes=["read_content", "read_user"],
                    config={
                        "name": "Notion",
                        "category": "Knowledge",
                        "oauth": {
                            "access_token": encrypt_secret("secret_notion_token", settings),
                            "expires_at": None,
                            "token_type": "bearer",
                        },
                        "profile": {
                            "sub": f"notion-{uuid.uuid4().hex[:8]}",
                            "workspace_name": "Test Workspace",
                        },
                        "notion": {},
                    },
                    connected_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _page(
    page_id: str,
    title: str,
    *,
    edited: str,
    status: str | None = "In progress",
    due: str | None = None,
    archived: bool = False,
    parent_db: str | None = None,
) -> dict:
    props: dict = {
        "Name": {
            "type": "title",
            "title": [{"type": "text", "plain_text": title, "text": {"content": title}}],
        }
    }
    if status:
        props["Status"] = {
            "type": "status",
            "status": {"name": status},
        }
    if due:
        props["Due"] = {"type": "date", "date": {"start": due}}
    parent = {"type": "workspace", "workspace": True}
    if parent_db:
        parent = {"type": "database_id", "database_id": parent_db}
    return {
        "object": "page",
        "id": page_id,
        "archived": archived,
        "url": f"https://www.notion.so/{page_id.replace('-', '')}",
        "last_edited_time": edited,
        "parent": parent,
        "properties": props,
    }


# -- OAuth -------------------------------------------------------------------


def test_notion_start_requires_configuration(monkeypatch):
    monkeypatch.setenv("NOTION_CLIENT_ID", "")
    monkeypatch.setenv("NOTION_CLIENT_SECRET", "")
    get_settings.cache_clear()
    try:
        response = client.get("/auth/oauth/notion/start")
        assert response.status_code == 503
    finally:
        get_settings.cache_clear()


def test_notion_start_returns_authorization_url(monkeypatch):
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        response = client.get("/auth/oauth/notion/start")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "notion"
        assert data["authorizationUrl"].startswith(NOTION_AUTH_URL)
        params = parse_qs(urlparse(data["authorizationUrl"]).query)
        assert params["client_id"] == ["test-notion-client-id"]
        assert params["response_type"] == ["code"]
        assert params["owner"] == ["user"]
    finally:
        get_settings.cache_clear()


def test_notion_callback_links_to_signed_in_user(monkeypatch):
    email = f"notion-owner-{uuid.uuid4().hex[:10]}@example.com"
    for key, value in _settings().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    try:
        user = _seed_user(email, with_notion=False)
        # Create Briefly session via linking state
        start = client.get(
            "/auth/oauth/notion/start",
            headers={"Authorization": f"Bearer {_issue_access(user)}"},
        )
        assert start.status_code == 200
        state = start.json()["state"]

        from app.integrations.oauth import types as oauth_types

        token_set = oauth_types.OAuthTokenSet(
            access_token="secret_notion_access",
            refresh_token=None,
            expires_at=None,
            token_type="bearer",
        )
        profile = oauth_types.OAuthProfile(
            subject=f"notion-sub-{uuid.uuid4().hex[:8]}",
            email=f"notion+bot@users.notion.local",
            email_verified=False,
            full_name="Briefly Bot",
            raw={"workspace_name": "Arcadia WS", "workspace_id": "ws-1"},
        )
        monkeypatch.setattr(NotionOAuthProvider, "exchange_code", lambda self, code: token_set)
        monkeypatch.setattr(NotionOAuthProvider, "fetch_profile", lambda self, token: profile)

        response = client.get(
            f"/auth/oauth/notion/callback?code=notion-code&state={state}"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == email

        db = SessionLocal()
        try:
            row = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "notion")
                .one()
            )
            assert row.status == "connected"
            assert row.account == "Arcadia WS"
            assert row.config["oauth"]["expires_at"] is None
            assert row.config["oauth"]["access_token"]
        finally:
            db.close()
    finally:
        _cleanup_email(email)
        get_settings.cache_clear()


def _issue_access(user: User) -> str:
    from app.services.auth_service import AuthService

    db = SessionLocal()
    try:
        tokens = AuthService(db).issue_tokens(db.get(User, user.id))
        return tokens.accessToken
    finally:
        db.close()


def test_notion_long_lived_token_refresh_returns_access(monkeypatch):
    email = f"notion-tok-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        from app.services.oauth_service import OAuthService

        db = SessionLocal()
        try:
            access = OAuthService(db).refresh_provider_access_token(
                db.get(User, user.id), "notion"
            )
            assert access == "secret_notion_token"
        finally:
            db.close()
    finally:
        _cleanup_email(email)


# -- Sync --------------------------------------------------------------------


class _FakeNotionClient:
    def __init__(self, pages=None, databases=None, db_pages=None):
        self.pages = pages or []
        self.databases = databases or []
        self.db_pages = db_pages or {}
        self.search_calls = 0

    def search(self, *, query=None, filter_object=None, start_cursor=None, page_size=100):
        self.search_calls += 1
        if filter_object == "database":
            return {"results": self.databases, "has_more": False, "next_cursor": None}
        return {"results": self.pages, "has_more": False, "next_cursor": None}

    def query_database(self, database_id, *, start_cursor=None, page_size=100, filter_body=None):
        items = self.db_pages.get(database_id, [])
        if filter_body:
            watermark = (
                (filter_body.get("last_edited_time") or {}).get("on_or_after")
            )
            if watermark:
                items = [i for i in items if i.get("last_edited_time", "") >= watermark]
        return {"results": items, "has_more": False, "next_cursor": None}

    def list_block_children(self, block_id, *, page_size=20):
        return {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"plain_text": f"Preview for {block_id}", "type": "text"}
                        ]
                    },
                }
            ]
        }


def test_notion_sync_upserts_and_preserves_intelligence(monkeypatch):
    email = f"notion-sync-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        edited = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        page = _page("aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee", "Ship Q3 hiring plan", edited=edited)

        fake = _FakeNotionClient(pages=[page], databases=[])
        monkeypatch.setattr(
            "app.services.notion_sync_service.NotionClient",
            lambda token, settings=None: fake,
        )

        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            # Pre-seed AI intelligence that sync must preserve.
            item = NotionItem(
                user_id=u.id,
                external_id=page["id"],
                kind="task",
                title="old title",
                intelligence={"aiSummary": "keep me"},
                sources=["OpenAI"],
            )
            db.add(item)
            db.commit()

            counts = NotionSyncService(db).sync_user(u, reason="manual")
            assert counts["upserted"] >= 1

            row = (
                db.query(NotionItem)
                .filter(NotionItem.user_id == u.id, NotionItem.external_id == page["id"])
                .one()
            )
            assert row.title == "Ship Q3 hiring plan"
            assert row.intelligence.get("aiSummary") == "keep me"
            assert "Notion" in (row.sources or [])
            assert row.content_preview

            integ = (
                db.query(Integration)
                .filter(Integration.user_id == u.id, Integration.provider == "notion")
                .one()
            )
            assert integ.config["notion"].get("last_edited_watermark")
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_notion_incremental_skips_older_than_watermark(monkeypatch):
    email = f"notion-inc-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        new = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        watermark = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            integ = (
                db.query(Integration)
                .filter(Integration.user_id == u.id, Integration.provider == "notion")
                .one()
            )
            cfg = dict(integ.config or {})
            cfg["notion"] = {"last_edited_watermark": watermark, "selected_database_ids": []}
            integ.config = cfg
            db.commit()

            pages = [
                _page("old-page-id-0001-0002-000300040005", "Old page", edited=old),
                _page("new-page-id-0001-0002-000300040005", "New page", edited=new),
            ]
            # Search returns newest first (API sort).
            pages_sorted = sorted(pages, key=lambda p: p["last_edited_time"], reverse=True)
            fake = _FakeNotionClient(pages=pages_sorted, databases=[])
            monkeypatch.setattr(
                "app.services.notion_sync_service.NotionClient",
                lambda token, settings=None: fake,
            )

            NotionSyncService(db).sync_user(u, reason="manual")
            titles = {
                r.title
                for r in db.query(NotionItem).filter(NotionItem.user_id == u.id).all()
            }
            assert "New page" in titles
            assert "Old page" not in titles
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_notion_sync_marks_archived_as_deleted(monkeypatch):
    email = f"notion-del-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        edited = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        page_id = "dead1111-bbbb-cccc-dddd-eeeeeeeeeeee"
        page = _page(page_id, "Gone task", edited=edited, archived=True)

        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            db.add(
                NotionItem(
                    user_id=u.id,
                    external_id=page_id,
                    kind="task",
                    title="Gone task",
                    archived=False,
                )
            )
            db.commit()

            fake = _FakeNotionClient(pages=[page], databases=[])
            monkeypatch.setattr(
                "app.services.notion_sync_service.NotionClient",
                lambda token, settings=None: fake,
            )
            counts = NotionSyncService(db).sync_user(u, reason="manual")
            assert counts["deleted"] >= 1
            row = (
                db.query(NotionItem)
                .filter(NotionItem.user_id == u.id, NotionItem.external_id == page_id)
                .one()
            )
            assert row.archived is True
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_notion_sync_conflict_when_disconnected():
    email = f"notion-off-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email, with_notion=False)
        db = SessionLocal()
        try:
            from fastapi import HTTPException

            try:
                NotionSyncService(db).sync_user(db.get(User, user.id))
                assert False, "expected conflict"
            except HTTPException as exc:
                assert exc.status_code == 409
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_integrations_sync_triggers_notion(monkeypatch):
    email = f"notion-api-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        called = {"ok": False}

        def _fake_sync(self, u, *, reason="manual"):
            called["ok"] = True
            return {"upserted": 0, "deleted": 0, "pages": 0}

        monkeypatch.setattr(NotionSyncService, "sync_user", _fake_sync)
        token = _issue_access(user)
        response = client.post(
            "/integrations/notion/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert called["ok"] is True
    finally:
        _cleanup_email(email)


# -- Morning Brief / Ask / Overview ------------------------------------------


def test_ai_context_includes_notion_when_connected():
    email = f"notion-ai-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            due = datetime.now(timezone.utc) + timedelta(hours=4)
            db.add(
                NotionItem(
                    user_id=u.id,
                    external_id="task-1",
                    kind="task",
                    title="Approve hiring plan",
                    status="Blocked",
                    due_at=due,
                    content_preview="Waiting on board",
                )
            )
            db.add(
                NotionItem(
                    user_id=u.id,
                    external_id="dec-1",
                    kind="decision",
                    title="Decision: expand APAC",
                )
            )
            db.commit()

            ctx = AIService(db, u)._morning_brief_context()
            assert ctx["notion"]["connected"] is True
            assert any(
                t["title"] == "Approve hiring plan"
                for t in ctx["notion"]["outstandingTasks"]
            )
            assert any("block" in t["status"].lower() for t in ctx["notion"]["blocked"])
            assert ctx["notion"]["decisions"]

            ask = AIService(db, u)._ask_context()
            assert "notion" in ask
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_ai_context_notion_empty_when_disconnected():
    email = f"notion-ai-off-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email, with_notion=False)
        db = SessionLocal()
        try:
            ctx = AIService(db, db.get(User, user.id))._morning_brief_context()
            assert ctx["notion"]["connected"] is False
            assert ctx["notion"]["outstandingTasks"] == []
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_overview_surfaces_notion_tasks():
    email = f"notion-ov-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            now = datetime.now(timezone.utc)
            db.add(
                NotionItem(
                    user_id=u.id,
                    external_id="ov-task",
                    kind="task",
                    title="Today Notion task",
                    status="Open",
                    due_at=now + timedelta(hours=2),
                    last_edited_at=now,
                )
            )
            db.add(
                NotionItem(
                    user_id=u.id,
                    external_id="ov-note",
                    kind="note",
                    title="Edited doc",
                    last_edited_at=now,
                    content_preview="Latest notes",
                )
            )
            db.commit()

            overview = OverviewService(db, u).get_overview()
            titles = [f.title for f in overview.focus]
            assert any("Today Notion task" in t for t in titles)
            assert any(a.source == "Notion" for a in overview.activity)
            assert any(a.label == "Today Notion task" for a in overview.executiveSummary.recommendedActions)
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_overview_fallback_without_notion_items():
    """Connected Notion with zero items must not change Overview shape vs empty path."""
    email = f"notion-ov-empty-{uuid.uuid4().hex[:10]}@example.com"
    get_settings.cache_clear()
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            overview = OverviewService(db, db.get(User, user.id)).get_overview()
            # Non-demo user, no items → empty lists (identical pre-Notion behaviour).
            assert overview.focus == []
            assert overview.activity == []
        finally:
            db.close()
    finally:
        _cleanup_email(email)
