import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.schemas.daily_brief import DailyBriefSchema
from app.services import mock_data
from app.services.daily_brief_service import DailyBriefService

client = TestClient(app)


def _fake_brief() -> DailyBriefSchema:
    """A brief shaped like one read from PostgreSQL, for tests that should not
    depend on `daily_briefs` actually being migrated yet."""
    return DailyBriefSchema(
        id=str(uuid.uuid4()),
        generatedAt=datetime.now(timezone.utc),
        summary="Database-backed summary for a test run.",
        priorities=[
            {
                "id": "pri_db_1",
                "rank": 1,
                "title": "Database-sourced priority",
                "detail": "Came from PostgreSQL, not mock_data.",
                "urgency": "high",
                "owner": "Lydia",
                "source": "Notion",
            }
        ],
        risks=[
            {
                "id": "risk_db_1",
                "title": "Database-sourced risk",
                "detail": "Came from PostgreSQL, not mock_data.",
                "severity": "medium",
                "impact": "Test impact",
                "mitigation": "Test mitigation",
                "source": "Gmail",
            }
        ],
        recommendations=[
            {"id": "rec_1", "title": "Test recommendation", "rationale": "Because tests"}
        ],
        executiveScore=81,
        createdAt=datetime.now(timezone.utc),
    )


def test_daily_brief_latest_returns_404_when_none_exists(monkeypatch):
    monkeypatch.setattr(DailyBriefService, "get_latest_brief", lambda self: None)

    response = client.get("/daily-brief/latest")
    assert response.status_code == 404


def test_daily_brief_latest_returns_the_persisted_brief(monkeypatch):
    fake = _fake_brief()
    monkeypatch.setattr(DailyBriefService, "get_latest_brief", lambda self: fake)

    response = client.get("/daily-brief/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == fake.summary
    assert data["executiveScore"] == 81
    assert data["priorities"][0]["id"] == "pri_db_1"


def test_overview_falls_back_to_mock_data_when_no_brief_exists(monkeypatch):
    monkeypatch.setattr(DailyBriefService, "get_latest_brief", lambda self: None)

    response = client.get("/overview")
    assert response.status_code == 200
    summary = response.json()["executiveSummary"]
    assert summary["summary"] == mock_data.EXECUTIVE_SUMMARY_TEXT
    assert summary["priorities"][0]["id"] == mock_data.PRIORITIES[0]["id"]


def test_overview_falls_back_when_the_database_is_unreachable(monkeypatch):
    def _raise(self):
        raise SQLAlchemyError("connection refused")

    monkeypatch.setattr(DailyBriefService, "get_latest_brief", _raise)

    response = client.get("/overview")
    assert response.status_code == 200
    assert response.json()["executiveSummary"]["summary"] == mock_data.EXECUTIVE_SUMMARY_TEXT


def test_overview_prefers_the_database_when_a_brief_exists(monkeypatch):
    fake = _fake_brief()
    monkeypatch.setattr(DailyBriefService, "get_latest_brief", lambda self: fake)

    response = client.get("/overview")
    assert response.status_code == 200
    data = response.json()

    summary = data["executiveSummary"]
    assert summary["summary"] == fake.summary
    assert summary["priorities"][0]["id"] == "pri_db_1"
    assert summary["risks"][0]["id"] == "risk_db_1"

    # Only summary/priorities/risks moved to the database — everything else
    # in this phase is still mock_data, unaffected by which brief was found.
    assert len(data["kpis"]) == len(mock_data.KPIS)
    assert len(data["activity"]) == len(mock_data.ACTIVITY)
    assert len(data["focus"]) == len(mock_data.TODAYS_FOCUS)
