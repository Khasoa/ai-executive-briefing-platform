from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Integration, SyncEvent
from app.services import demo_data

client = TestClient(app)


def _fake_integration_row(**overrides) -> Integration:
    """An `Integration` ORM instance built in memory (never added to a
    session or committed), shaped like a row read from PostgreSQL."""
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        provider="database-provider",
        status="connected",
        account="db-user@example.com",
        scopes=["scope.readonly"],
        config={
            "name": "Database Provider",
            "category": "Testing",
            "description": "Database-backed integration for tests.",
            "metrics": [{"label": "Items", "value": "5"}],
            "poweredBy": "Database Provider API",
        },
        last_sync_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        connected_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    defaults.update(overrides)
    return Integration(**defaults)


def _fake_sync_event_row(integration: Integration, **overrides) -> SyncEvent:
    defaults = dict(
        id=uuid4(),
        integration_id=integration.id,
        event="Database-backed sync completed",
        status="success",
        detail="Came from PostgreSQL, not demo_data.",
        occurred_at=datetime.now(timezone.utc) - timedelta(minutes=3),
    )
    defaults.update(overrides)
    event = SyncEvent(**defaults)
    event.integration = integration
    return event


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for IntegrationService."""

    def __init__(self, rows):
        self._rows = list(rows)

    def order_by(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _patch_session(monkeypatch, *, integrations=None, sync_events=None, raise_error=False):
    """Patches `Session` so IntegrationService runs its real query/write logic."""

    from app.models import User
    from app.services.demo_user import DEMO_USER, DEMO_USER_FALLBACK_ID

    tables = {
        Integration: list(integrations or []),
        SyncEvent: list(sync_events or []),
        User: [
            User(id=DEMO_USER_FALLBACK_ID, **DEMO_USER, hashed_password="!"),
        ],
    }

    def _fake_query(self, model, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        return _FakeQuery(tables.get(model, []))

    def _add(self, instance):
        if getattr(instance, "id", None) is None:
            instance.id = uuid4()
        # Attach the parent integration so `_sync_event_to_dict` can read it
        # after a write without a real relationship loader.
        if isinstance(instance, SyncEvent) and instance.integration is None:
            parent = next(
                (row for row in tables[Integration] if row.id == instance.integration_id),
                None,
            )
            instance.integration = parent
        tables.setdefault(type(instance), []).append(instance)

    def _noop(self, *args, **kwargs):
        return None

    monkeypatch.setattr(Session, "query", _fake_query)
    monkeypatch.setattr(Session, "add", _add)
    monkeypatch.setattr(Session, "commit", _noop)
    monkeypatch.setattr(Session, "refresh", _noop)
    monkeypatch.setattr(Session, "rollback", _noop)
    return tables


def test_integrations_are_returned_from_postgres_when_rows_exist(monkeypatch):
    rows = [
        _fake_integration_row(provider="database-provider", status="connected"),
        _fake_integration_row(
            provider="second-database-provider", status="not-connected", account=None
        ),
    ]
    _patch_session(monkeypatch, integrations=rows)

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    ids = {i["id"] for i in data["integrations"]}
    # Canonical catalog is always present; extra user-owned rows are appended.
    assert "google-calendar" in ids
    assert "gmail" in ids
    assert "notion" in ids
    assert {"database-provider", "second-database-provider"}.issubset(ids)
    assert data["totalCount"] >= len(ids)

    first = next(i for i in data["integrations"] if i["id"] == "database-provider")
    assert first["name"] == "Database Provider"
    assert first["description"] == "Database-backed integration for tests."
    assert first["metrics"] == [{"label": "Items", "value": "5"}]
    assert first["poweredBy"] == "Database Provider API"
    assert first["lastSyncLabel"].endswith("ago")


def test_integrations_fall_back_to_demo_data_when_table_is_empty(monkeypatch):
    _patch_session(monkeypatch, integrations=[], sync_events=[])

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    assert {i["id"] for i in demo_data.INTEGRATIONS}.issubset(
        {i["id"] for i in data["integrations"]}
    )
    assert data["totalCount"] >= len(demo_data.INTEGRATIONS)
    assert data["syncHistory"] == demo_data.SYNC_HISTORY


def test_integrations_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_session(monkeypatch, raise_error=True)

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    # Demo user still gets the curated catalog overlay; sync history falls back.
    assert {i["id"] for i in demo_data.INTEGRATIONS}.issubset(
        {i["id"] for i in data["integrations"]}
    )
    assert data["syncHistory"] == demo_data.SYNC_HISTORY


def test_sync_history_is_returned_from_postgres_when_rows_exist(monkeypatch):
    integration = _fake_integration_row(provider="gmail", status="connected")
    event = _fake_sync_event_row(integration)
    _patch_session(monkeypatch, integrations=[integration], sync_events=[event])

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    assert len(data["syncHistory"]) == 1
    assert data["syncHistory"][0]["id"] == str(event.id)
    assert data["syncHistory"][0]["integrationId"] == "gmail"
    assert data["syncHistory"][0]["detail"] == "Came from PostgreSQL, not demo_data."


def test_sync_persists_event_against_database_backed_integrations(monkeypatch):
    row = _fake_integration_row(provider="database-provider", status="connected")
    tables = _patch_session(monkeypatch, integrations=[row], sync_events=[])

    response = client.post("/integrations/database-provider/sync")
    assert response.status_code == 200
    data = response.json()

    synced = next(i for i in data["integrations"] if i["id"] == "database-provider")
    assert synced["status"] == "syncing"
    assert synced["lastSyncLabel"] == "syncing now"
    assert len(tables[SyncEvent]) == 1
    assert tables[SyncEvent][0].event == "Manual sync started"
    assert data["syncHistory"][0]["integrationId"] == "database-provider"
