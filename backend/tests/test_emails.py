from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import Email
from app.services import demo_data
from app.services.inbox_service import InboxService

client = TestClient(app)

ATHENS = timezone(timedelta(hours=3))


def _fake_email_row(**overrides) -> Email:
    """An `Email` ORM instance built in memory (never added to a session or
    committed), shaped like a row read from PostgreSQL. This lets tests
    exercise `InboxService`'s real query/mapping logic without depending on
    `emails` actually being migrated in a live database yet."""
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        external_id=None,
        thread_id="thread_test",
        category="needs-reply",
        subject="Database-backed subject",
        sender={"name": "Test Sender", "email": "test@example.com", "company": "Test Co", "avatar": "TS"},
        ai_summary="Database-backed AI summary.",
        priority="high",
        suggested_response="Database-backed suggested response.",
        reading_time="2 min",
        thread_count=3,
        unread=True,
        labels=["Database", "Test"],
        received_at=datetime(2026, 8, 4, 9, 0, tzinfo=ATHENS),
    )
    defaults.update(overrides)
    return Email(**defaults)


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for `InboxService.list_emails()`."""

    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


def _patch_query(monkeypatch, *, rows=None, raise_error=False):
    """Patches `Session.query` for one test so `list_emails()` runs its
    real try/except and empty-table checks against a fake result set,
    instead of either hitting a live database or bypassing the fallback
    logic entirely by monkeypatching a higher-level method."""

    def _fake_query(self, *args, **kwargs):
        if raise_error:
            raise SQLAlchemyError("connection refused")
        return _FakeQuery(rows or [])

    monkeypatch.setattr(Session, "query", _fake_query)


def test_emails_are_returned_from_postgres_when_rows_exist(monkeypatch):
    rows = [
        _fake_email_row(subject="Database Email One", category="needs-reply"),
        _fake_email_row(subject="Database Email Two", category="high-priority"),
    ]
    _patch_query(monkeypatch, rows=rows)

    response = client.get("/inbox")
    assert response.status_code == 200
    data = response.json()

    subjects = {email["subject"] for email in data["emails"]}
    assert subjects == {"Database Email One", "Database Email Two"}

    first = next(e for e in data["emails"] if e["subject"] == "Database Email One")
    assert first["aiSummary"] == "Database-backed AI summary."
    assert first["sender"]["name"] == "Test Sender"
    assert first["threadCount"] == 3
    assert first["unread"] is True

    # Category counts reflect the database-backed list, not demo_data.
    categories_by_id = {c["id"]: c["count"] for c in data["categories"]}
    assert categories_by_id["needs-reply"] == 1
    assert categories_by_id["high-priority"] == 1
    assert categories_by_id["waiting"] == 0


def test_emails_fall_back_to_demo_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    response = client.get("/inbox")
    assert response.status_code == 200
    data = response.json()

    assert {e["id"] for e in data["emails"]} == {e["id"] for e in demo_data.EMAILS}
    # Summary stats are independent aggregate figures, not derived from the
    # curated list, so they stay sourced from demo_data either way.
    assert data["summary"] == demo_data.INBOX_SUMMARY


def test_emails_fall_back_when_the_database_is_unreachable(monkeypatch):
    _patch_query(monkeypatch, raise_error=True)

    response = client.get("/inbox")
    assert response.status_code == 200
    data = response.json()

    assert {e["id"] for e in data["emails"]} == {e["id"] for e in demo_data.EMAILS}


def test_get_email_reads_from_postgres_when_rows_exist(monkeypatch):
    row = _fake_email_row(subject="Database Email One")
    _patch_query(monkeypatch, rows=[row])

    # `Session()` here is never actually connected to anything — `query()`
    # is monkeypatched away entirely, so no real database access happens.
    email = InboxService(db=Session()).get_email(str(row.id))
    assert email.subject == "Database Email One"
    assert email.aiSummary == "Database-backed AI summary."


def test_get_email_falls_back_to_mock_data_when_table_is_empty(monkeypatch):
    _patch_query(monkeypatch, rows=[])

    mock_email = demo_data.EMAILS[0]
    email = InboxService(db=Session()).get_email(mock_email["id"])
    assert email.subject == mock_email["subject"]
