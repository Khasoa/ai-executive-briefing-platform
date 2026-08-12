from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Opportunity, User
from app.services import demo_data
from app.services.crm_service import CRMService
from app.services.demo_user import DEMO_USER, DEMO_USER_FALLBACK_ID

client = TestClient(app)


def _demo_user() -> User:
    return User(id=DEMO_USER_FALLBACK_ID, **DEMO_USER, hashed_password="!")


def _fake_opportunity_row(**overrides) -> Opportunity:
    """An `Opportunity` ORM instance built in memory (never added to a
    session or committed), shaped like a row read from PostgreSQL. This lets
    tests exercise `CRMService`'s real query/mapping logic without depending
    on `opportunities` actually being migrated in a live database yet."""
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        external_id=None,
        company="Database Corp",
        logo="DC",
        industry="Software",
        stage="Proposal",
        value=250_000.0,
        probability=45,
        owner="Test Owner",
        close_date=date(2026, 8, 15),
        risk_level="high",
        last_interaction={
            "type": "email",
            "summary": "Database-backed last interaction.",
            "time": "Yesterday",
            "sources": ["Gmail"],
        },
        ai_summary="Database-backed AI summary.",
        recommended_action="Database-backed recommended action.",
        signals=["Database signal one"],
    )
    defaults.update(overrides)
    return Opportunity(**defaults)


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for list + auth demo lookup."""

    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _patch_query(monkeypatch, *, rows=None, raise_error=False):
    """Patches `Session.query` for one test so `list_opportunities()` runs
    its real try/except and empty-table checks against a fake result set,
    instead of either hitting a live database or bypassing the fallback
    logic entirely by monkeypatching a higher-level method."""

    def _fake_query(self, model=None, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        if model is User:
            return _FakeQuery([_demo_user()])
        return _FakeQuery(rows or [])

    monkeypatch.setattr(Session, "query", _fake_query)


def test_opportunities_are_returned_from_postgres_when_rows_exist(monkeypatch):
    rows = [
        _fake_opportunity_row(company="Database Corp", risk_level="high", value=250_000.0, probability=45),
        _fake_opportunity_row(company="Second Database Co", risk_level="low", value=100_000.0, probability=80),
    ]
    _patch_query(monkeypatch, rows=rows)

    response = client.get("/crm")
    assert response.status_code == 200
    data = response.json()

    companies = {o["company"] for o in data["opportunities"]}
    assert companies == {"Database Corp", "Second Database Co"}

    first = next(o for o in data["opportunities"] if o["company"] == "Database Corp")
    assert first["closeDate"] == "Aug 15, 2026"
    assert first["value"] == 250_000
    assert first["aiSummary"] == "Database-backed AI summary."
    assert first["sources"] == ["Gmail"]
    assert first["lastInteraction"]["summary"] == "Database-backed last interaction."

    # Summary figures are derived from whichever list was actually loaded.
    assert data["summary"]["pipelineValue"] == 350_000
    assert data["summary"]["needingAttention"] == 1  # only the "high" risk one


def test_opportunities_fall_back_to_demo_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/crm")
    assert response.status_code == 200
    data = response.json()

    assert {o["id"] for o in data["opportunities"]} == {o["id"] for o in demo_data.OPPORTUNITIES}


def test_opportunities_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_query(monkeypatch, raise_error=True)

    response = client.get("/crm")
    assert response.status_code == 200
    data = response.json()

    assert {o["id"] for o in data["opportunities"]} == {o["id"] for o in demo_data.OPPORTUNITIES}


def test_get_opportunity_reads_from_postgres_when_rows_exist(monkeypatch):
    row = _fake_opportunity_row(company="Database Corp")
    _patch_query(monkeypatch, rows=[row])

    # `Session()` here is never actually connected to anything — `query()`
    # is monkeypatched away entirely, so no real database access happens.
    opportunity = CRMService(db=Session(), user=_demo_user()).get_opportunity(str(row.id))
    assert opportunity.company == "Database Corp"
    assert opportunity.aiSummary == "Database-backed AI summary."


def test_get_opportunity_falls_back_to_mock_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    mock_opportunity = demo_data.OPPORTUNITIES[0]
    opportunity = CRMService(db=Session(), user=_demo_user()).get_opportunity(
        mock_opportunity["id"]
    )
    assert opportunity.company == mock_opportunity["company"]


def test_unknown_opportunity_raises_404(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    try:
        CRMService(db=Session(), user=_demo_user()).get_opportunity("not-a-real-id")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
