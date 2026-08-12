from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Meeting, User
from app.services import demo_data
from app.services.demo_user import DEMO_USER, DEMO_USER_FALLBACK_ID

client = TestClient(app)

ATHENS = timezone(timedelta(hours=3))


def _demo_user() -> User:
    return User(id=DEMO_USER_FALLBACK_ID, **DEMO_USER, hashed_password="!")


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
    """Just enough of the SQLAlchemy `Query` surface for list + auth demo lookup."""

    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _patch_query(monkeypatch, *, rows=None, raise_error=False):
    """Patches `Session.query` for one test so `list_meetings()` runs its
    real try/except and empty-table checks against a fake result set,
    instead of either hitting a live database or bypassing the fallback
    logic entirely by monkeypatching a higher-level method."""

    def _fake_query(self, model=None, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        if model is User:
            return _FakeQuery([_demo_user()])
        # Meeting list/detail paths query Meeting; related-context queries
        # (Email/Opportunity/WorkItem) should see an empty set under this stub.
        from app.models import Meeting as MeetingModel

        if model is MeetingModel:
            return _FakeQuery(rows or [])
        return _FakeQuery([])

    monkeypatch.setattr(Session, "query", _fake_query)


def test_meetings_are_returned_from_postgres_when_rows_exist(monkeypatch):
    # Pin midday UTC so timezone conversion cannot push events into tomorrow.
    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    rows = [
        _fake_meeting_row(
            title="Database Sync",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=1, minutes=30),
        ),
        _fake_meeting_row(
            title="Second Database Meeting",
            starts_at=now + timedelta(hours=3),
            ends_at=now + timedelta(hours=3, minutes=20),
        ),
    ]
    _patch_query(monkeypatch, rows=rows)

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == 2
    assert data["todayCount"] == 2
    titles = {m["title"] for m in data["meetings"]}
    assert titles == {"Database Sync", "Second Database Meeting"}

    first = next(m for m in data["meetings"] if m["title"] == "Database Sync")
    assert first["duration"] == "30 min"
    assert first["window"] == "today"
    assert first["timingLabel"]
    assert first["preparationNotes"] == ["Database-backed preparation note."]
    assert first["risks"][0]["title"] == "Risk"
    assert "today" in data["windows"]
    assert len(data["windows"]["today"]) == 2


def test_meetings_fall_back_to_demo_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == len(demo_data.MEETINGS)
    assert {m["id"] for m in data["meetings"]} == {m["id"] for m in demo_data.MEETINGS}


def test_meetings_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_query(monkeypatch, raise_error=True)

    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()

    assert data["meetingCount"] == len(demo_data.MEETINGS)
    assert {m["id"] for m in data["meetings"]} == {m["id"] for m in demo_data.MEETINGS}


def test_single_meeting_endpoint_reads_from_postgres_when_rows_exist(monkeypatch):
    now = datetime.now(timezone.utc)
    row = _fake_meeting_row(
        title="Database Sync",
        starts_at=now + timedelta(hours=2),
        ends_at=now + timedelta(hours=2, minutes=30),
    )
    _patch_query(monkeypatch, rows=[row])

    response = client.get(f"/meetings/{row.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Database Sync"


def test_single_meeting_endpoint_404s_against_demo_data_when_id_unknown(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/meetings/not-a-real-id")
    assert response.status_code == 404
