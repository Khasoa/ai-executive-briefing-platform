"""Live integration-card metrics from domain tables (not catalog placeholders)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Email,
    Integration,
    Meeting,
    MorningBrief,
    NotionItem,
    Opportunity,
    RefreshToken,
    SyncEvent,
    User,
    WorkItem,
)
from app.services.integration_catalog import disconnected_entry, SUPPORTED_INTEGRATIONS

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
        db.query(Meeting).filter(Meeting.user_id == user.id).delete()
        db.query(Email).filter(Email.user_id == user.id).delete()
        db.query(WorkItem).filter(WorkItem.user_id == user.id).delete()
        db.query(NotionItem).filter(NotionItem.user_id == user.id).delete()
        db.query(Opportunity).filter(Opportunity.user_id == user.id).delete()
        db.query(MorningBrief).filter(MorningBrief.user_id == user.id).delete()
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
            name="Metrics",
            full_name="Metrics User",
            role="CEO",
            company="Test",
            avatar="MU",
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


def _metric_map(integration: dict) -> dict[str, str]:
    return {m["label"]: m["value"] for m in integration.get("metrics") or []}


def test_connected_integrations_return_live_numeric_metrics(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-metrics")
    get_settings.cache_clear()
    email = f"metrics-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
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
                        "oauth": {
                            "access_token": encrypt_secret("tok", settings),
                            "refresh_token": encrypt_secret("ref", settings),
                            "expires_at": (now + timedelta(hours=1)).isoformat(),
                        },
                        "metrics": [
                            {"label": "Meetings today", "value": "—"},
                            {"label": "Calendars", "value": "—"},
                        ],
                    },
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            db.add(
                Integration(
                    user_id=user.id,
                    provider="clickup",
                    status="connected",
                    account="cu@example.com",
                    scopes=["tasks.read"],
                    config={
                        "clickup": {"team_ids": ["t1"]},
                        "metrics": [
                            {"label": "Tasks synced", "value": "—"},
                            {"label": "Workspaces", "value": "—"},
                        ],
                    },
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            db.add(
                Integration(
                    user_id=user.id,
                    provider="monday",
                    status="connected",
                    account="mon@example.com",
                    scopes=["boards:read"],
                    config={"monday": {}},
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            db.add(
                Integration(
                    user_id=user.id,
                    provider="notion",
                    status="connected",
                    account="notion@example.com",
                    scopes=["read_content"],
                    config={"notion": {"selected_database_ids": ["db1"]}},
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            db.add(
                Integration(
                    user_id=user.id,
                    provider="gohighlevel",
                    status="connected",
                    account="ghl@example.com",
                    scopes=["opportunities.readonly"],
                    config={"ghl": {"location_id": "loc1"}},
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            db.add(
                Meeting(
                    user_id=user.id,
                    external_id="cal:m1",
                    title="Standup",
                    starts_at=now + timedelta(hours=1),
                    ends_at=now + timedelta(hours=2),
                    type="internal",
                    location="",
                    prep_status="needs-prep",
                )
            )
            # Zero emails intentionally — Needs reply / Threads must be "0" not "—"
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="clickup",
                    external_id="clickup:task-1",
                    title="Task A",
                    workspace_id="t1",
                    workspace_name="WS",
                    archived=False,
                )
            )
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="monday",
                    external_id="monday:item-1",
                    title="Board item",
                    container_id="b1",
                    container_name="Board",
                    archived=False,
                )
            )
            db.add(
                NotionItem(
                    user_id=user.id,
                    external_id="notion:p1",
                    object_type="page",
                    title="Page",
                    parent_database_id="db1",
                    archived=False,
                )
            )
            db.add(
                Opportunity(
                    user_id=user.id,
                    company="Acme",
                    stage="Proposal",
                    value=1000,
                    probability=50,
                    owner="You",
                )
            )
            db.add(
                MorningBrief(
                    user_id=user.id,
                    brief_date=date.today(),
                    headline="Hello",
                    executive_summary="Summary",
                    confidence="medium",
                    sources=[],
                    sections={},
                    closing={},
                )
            )
            db.commit()
        finally:
            db.close()

        token = _issue_access(user)
        response = client.get(
            "/integrations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        by_id = {i["id"]: i for i in response.json()["integrations"]}

        cal = _metric_map(by_id["google-calendar"])
        assert cal["Meetings today"] == "1"
        assert cal["Calendars"] == "1"
        assert cal["Meetings today"] != "—"

        gmail = _metric_map(by_id["gmail"])
        assert gmail["Threads indexed"] == "0"
        assert gmail["Needs reply"] == "0"

        clickup = _metric_map(by_id["clickup"])
        assert clickup["Tasks synced"] == "1"
        assert clickup["Workspaces"] == "1"

        monday = _metric_map(by_id["monday"])
        assert monday["Items synced"] == "1"
        assert monday["Boards"] == "1"

        notion = _metric_map(by_id["notion"])
        assert notion["Pages indexed"] == "1"
        assert notion["Databases"] == "1"

        ghl = _metric_map(by_id["gohighlevel"])
        assert ghl["Opportunities"] == "1"
        # Pipeline name is not reliably stored — stay honest.
        assert ghl["Pipeline"] == "—"

        openai = _metric_map(by_id["openai"])
        assert openai["Briefs generated"] == "1"
        assert openai["Model"] != "—"

        n8n = _metric_map(by_id["n8n"])
        assert n8n["Runs this month"] == "—"

        assert by_id["google-calendar"]["status"] == "connected"
        assert by_id["clickup"]["status"] == "connected"
    finally:
        _cleanup(email)
        get_settings.cache_clear()


def test_disconnected_integrations_keep_placeholder_metrics():
    email = f"disc-metrics-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        token = _issue_access(user)
        response = client.get(
            "/integrations", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        by_id = {i["id"]: i for i in response.json()["integrations"]}
        for entry in SUPPORTED_INTEGRATIONS:
            if entry["auth"] in ("api_key", "webhook"):
                continue
            card = by_id[entry["id"]]
            assert card["status"] == "not-connected"
            expected = disconnected_entry(entry)["metrics"]
            assert card["metrics"] == expected
            assert all(m["value"] == "—" for m in card["metrics"])
    finally:
        _cleanup(email)


def test_gmail_needs_reply_counts_priority_categories():
    email = f"gmail-metrics-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            settings = get_settings()
            db.add(
                Integration(
                    user_id=user.id,
                    provider="google",
                    status="connected",
                    account=email,
                    scopes=["gmail.readonly"],
                    config={
                        "oauth": {
                            "access_token": encrypt_secret("tok", settings),
                            "refresh_token": encrypt_secret("ref", settings),
                            "expires_at": (now + timedelta(hours=1)).isoformat(),
                        }
                    },
                    last_sync_at=now,
                    connected_at=now,
                )
            )
            for i, category in enumerate(("needs-reply", "promotional", "high-priority")):
                db.add(
                    Email(
                        user_id=user.id,
                        external_id=f"msg-{i}",
                        category=category,
                        subject=f"Subj {i}",
                        sender={"email": "a@b.com"},
                        ai_summary="",
                        priority="medium",
                        unread=True,
                        received_at=now,
                    )
                )
            db.commit()
        finally:
            db.close()

        token = _issue_access(user)
        response = client.get(
            "/integrations", headers={"Authorization": f"Bearer {token}"}
        )
        gmail = _metric_map(
            next(i for i in response.json()["integrations"] if i["id"] == "gmail")
        )
        assert gmail["Threads indexed"] == "3"
        assert gmail["Needs reply"] == "2"
    finally:
        _cleanup(email)
