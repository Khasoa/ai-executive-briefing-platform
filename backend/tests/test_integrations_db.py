from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Integration
from app.services import mock_data

client = TestClient(app)


def _fake_integration_row(**overrides) -> Integration:
    """An `Integration` ORM instance built in memory (never added to a
    session or committed), shaped like a row read from PostgreSQL. This lets
    tests exercise `IntegrationService`'s real query/mapping logic without
    depending on `integrations` actually being migrated in a live database
    yet."""
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


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for `IntegrationService._load_integrations()`."""

    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


def _patch_query(monkeypatch, *, rows=None, raise_error=False):
    """Patches `Session.query` for one test so `_load_integrations()` runs
    its real try/except and empty-table checks against a fake result set,
    instead of either hitting a live database or bypassing the fallback
    logic entirely by monkeypatching a higher-level method."""

    def _fake_query(self, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        return _FakeQuery(rows or [])

    monkeypatch.setattr(Session, "query", _fake_query)


def test_integrations_are_returned_from_postgres_when_rows_exist(monkeypatch):
    rows = [
        _fake_integration_row(provider="database-provider", status="connected"),
        _fake_integration_row(provider="second-database-provider", status="not-connected", account=None),
    ]
    _patch_query(monkeypatch, rows=rows)

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    ids = {i["id"] for i in data["integrations"]}
    assert ids == {"database-provider", "second-database-provider"}
    assert data["totalCount"] == 2
    assert data["connectedCount"] == 1

    first = next(i for i in data["integrations"] if i["id"] == "database-provider")
    assert first["name"] == "Database Provider"
    assert first["description"] == "Database-backed integration for tests."
    assert first["metrics"] == [{"label": "Items", "value": "5"}]
    assert first["poweredBy"] == "Database Provider API"
    assert first["lastSyncLabel"].endswith("ago")


def test_integrations_fall_back_to_mock_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    assert {i["id"] for i in data["integrations"]} == {i["id"] for i in mock_data.INTEGRATIONS}
    assert data["totalCount"] == len(mock_data.INTEGRATIONS)


def test_integrations_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_query(monkeypatch, raise_error=True)

    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()

    assert {i["id"] for i in data["integrations"]} == {i["id"] for i in mock_data.INTEGRATIONS}


def test_sync_still_works_against_database_backed_integrations(monkeypatch):
    row = _fake_integration_row(provider="database-provider", status="connected")
    _patch_query(monkeypatch, rows=[row])

    response = client.post("/integrations/database-provider/sync")
    assert response.status_code == 200
    data = response.json()

    synced = next(i for i in data["integrations"] if i["id"] == "database-provider")
    assert synced["status"] == "syncing"
    assert synced["lastSyncLabel"] == "syncing now"
