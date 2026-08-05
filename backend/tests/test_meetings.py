from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Meeting
from app.services import mock_data

client = TestClient(app)

ATHENS = timezone(timedelta(hours=3))


def _fake_meeting_row(**overrides) -> Meeting:
    """A `Meeting` ORM instance built in memory (never added to a session or
    committed), shaped like a row read from PostgreSQL. This lets tests
    exercise `MeetingService`'s real query/mapping logic without depending
    on `meetings` actually being migrated in a live database yet."""
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        external_id=None,
        title="Database Sync",
        starts_at=datetime(2026, 8, 4, 9, 0, tzinfo=ATHENS),
        ends_at=datetime(2026, 8, 4, 9, 30, tzinfo=ATHENS),
        type="internal",
        location="Zoom",
        prep_status="ready",
        prep_reason="Test meeting sourced from PostgreSQL.",
        attendees=[{"name": "Test Person", "role": "CEO", "company": "Test Co", "avatar": "TP"}],
        agenda=["Database-backed agenda item"],
        company={
            "name": "Test Co",
            "industry": "Software",
            "size": "10 employees",
            "relationship": "Internal",
            "background": "Database-backed company background.",
        },
        intelligence={
            "relatedEmails": [],
            "preparationNotes": ["Database-backed preparation note."],
            "talkingPoints": ["Database-backed talking point."],
            "recommendedQuestions": ["Database-backed question?"],
            "risks": [{"title": "Risk", "detail": "Detail", "severity": "low"}],
        },
        sources=["Google Calendar"],
    )
    defaults.update(overrides)
    return Meeting(**defaults)


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for `MeetingService._load_meetings()`."""

    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


def _patch_query(monkeypatch, *, rows=None, raise_error=False):
    """Patches `Session.query` for one test so `_load_meetings()` runs its
    real try/except and empty-table checks against a fake result set,
    instead of either hitting a live database or bypassing the fallback
    logic entirely by monkeypatching a higher-level method."""

    def _fake_query(self, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        return _FakeQuery(rows or [])

    monkeypatch.setattr(Session, "query", _fake_query)


def test_meetings_are_returned_from_postgres_when_rows_exist(monkeypatch):
    rows = [
        _fake_meeting_row(
            title="Database Sync",
            starts_at=datetime(2026, 8, 4, 9, 0, tzinfo=ATHENS),
            ends_at=datetime(2026, 8, 4, 9, 30, tzinfo=ATHENS),
        ),
        _fake_meeting_row(
            title="Second Database Meeting",
            starts_at=datetime(2026, 8, 4, 11, 0, tzinfo=ATHENS),
            ends_at=datetime(2026, 8, 4, 11, 20, tzinfo=ATHENS),
        ),
    ]
    _patch_query(monkeypatch, rows=rows)

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == 2
    titles = {m["title"] for m in data["meetings"]}
    assert titles == {"Database Sync", "Second Database Meeting"}

    first = next(m for m in data["meetings"] if m["title"] == "Database Sync")
    # startTime/endTime/duration are derived from starts_at/ends_at, not stored directly.
    assert first["startTime"] == "09:00"
    assert first["endTime"] == "09:30"
    assert first["duration"] == "30 min"
    # relatedEmails/preparationNotes/talkingPoints/recommendedQuestions/risks
    # all come out of the single `intelligence` JSONB column.
    assert first["preparationNotes"] == ["Database-backed preparation note."]
    assert first["risks"][0]["title"] == "Risk"


def test_meetings_fall_back_to_mock_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == len(mock_data.MEETINGS)
    assert {m["id"] for m in data["meetings"]} == {m["id"] for m in mock_data.MEETINGS}


def test_meetings_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_query(monkeypatch, raise_error=True)

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == len(mock_data.MEETINGS)
    assert {m["id"] for m in data["meetings"]} == {m["id"] for m in mock_data.MEETINGS}


def test_single_meeting_endpoint_reads_from_postgres_when_rows_exist(monkeypatch):
    row = _fake_meeting_row(title="Database Sync")
    _patch_query(monkeypatch, rows=[row])

    response = client.get(f"/meetings/{row.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Database Sync"


def test_single_meeting_endpoint_404s_against_mock_data_when_id_unknown(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/meetings/not-a-real-id")
    assert response.status_code == 404
