"""Phase 7 — Morning Brief persistence.

Same testing approach as `test_meetings.py`, `test_integrations_db.py` etc:
patch `Session` so `MorningBriefService` runs its real query/write logic
against an in-memory fake instead of either hitting a live database or
bypassing the fallback logic by monkeypatching a higher-level method.

This service is the first one to *write* through the fallback-tested path
(`MorningBrief`/`BriefAction` are created, not just read), so the fake here
also covers `add`/`add_all`/`commit`/`refresh` — the read-only services'
fakes only needed `order_by`/`all`.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import BriefAction, MorningBrief, User
from app.services import demo_data

client = TestClient(app)


def _fake_brief_row(**overrides) -> MorningBrief:
    """A `MorningBrief` ORM instance built in memory (never added to a
    session or committed), shaped like a row read from PostgreSQL."""
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        brief_date=date(2026, 8, 4),
        headline="Database-backed headline for today.",
        executive_summary="Database-backed executive summary for today.",
        confidence="high",
        sources=["Gmail", "Notion"],
        sections={
            "priorities": [
                {
                    "id": "db_pri_1",
                    "rank": 1,
                    "title": "Database-sourced priority",
                    "detail": "Came from PostgreSQL, not demo_data.",
                    "urgency": "high",
                    "owner": "Lydia",
                    "source": "Notion",
                }
            ],
            "risks": [
                {
                    "id": "db_risk_1",
                    "title": "Database-sourced risk",
                    "detail": "Came from PostgreSQL, not demo_data.",
                    "severity": "medium",
                    "impact": "Test impact",
                    "mitigation": "Test mitigation",
                    "source": "Gmail",
                }
            ],
            "clients": [
                {
                    "id": "db_cli_1",
                    "company": "Database Co",
                    "stage": "Renewal",
                    "value": "$1",
                    "lastContact": "Today",
                    "reason": "Test reason",
                    "recommendedAction": "Test action",
                    "severity": "medium",
                }
            ],
            "focus": {
                "headline": "Database-sourced focus headline",
                "rationale": "Database-sourced rationale",
                "blocks": [],
            },
            "delegation": [
                {
                    "id": "db_del_1",
                    "task": "Database-sourced delegation",
                    "assignee": "Test Assignee",
                    "assigneeRole": "Test Role",
                    "reason": "Test reason",
                    "effort": "10 min saved",
                }
            ],
        },
        closing={
            "question": "Database-sourced question?",
            "answer": "Database-sourced answer.",
            "bullets": ["Database-sourced bullet."],
        },
        generated_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    defaults.update(overrides)
    return MorningBrief(**defaults)


def _fake_action_row(**overrides) -> BriefAction:
    defaults = dict(
        id=uuid4(),
        brief_id=uuid4(),
        label="Database-sourced checklist item",
        category="Decision",
        due="Today",
        done=False,
        completed_at=None,
    )
    defaults.update(overrides)
    return BriefAction(**defaults)


class _FakeQuery:
    """Just enough of the SQLAlchemy `Query` surface for `MorningBriefService`.

    `filter`/`order_by` are no-ops (like the other services' test fakes) —
    every test below only ever seeds the rows relevant to that one scenario,
    so "return everything" and "return the real filtered set" agree.
    """

    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _install_fake_db(monkeypatch, *, users=None, briefs=None, actions=None, raise_on_query=False):
    """Patches `Session` so `MorningBriefService` (and `get_or_create_demo_user`)
    run their real query/write logic against in-memory lists instead of a
    live database. Returns the `tables` dict so a test can inspect what got
    written (e.g. assert a `MorningBrief` was actually persisted).
    """
    tables: dict[type, list] = {
        User: list(users or []),
        MorningBrief: list(briefs or []),
        BriefAction: list(actions or []),
    }

    def _query(self, model, *args, **kwargs):
        if raise_on_query:
            raise SQLAlchemyError("connection refused")
        return _FakeQuery(tables.get(model, []))

    def _add(self, instance):
        if getattr(instance, "id", None) is None:
            instance.id = uuid4()
        tables.setdefault(type(instance), []).append(instance)

    def _add_all(self, instances):
        for instance in instances:
            _add(self, instance)

    def _noop(self, *args, **kwargs):
        return None

    monkeypatch.setattr(Session, "query", _query)
    monkeypatch.setattr(Session, "add", _add)
    monkeypatch.setattr(Session, "add_all", _add_all)
    monkeypatch.setattr(Session, "commit", _noop)
    monkeypatch.setattr(Session, "refresh", _noop)
    monkeypatch.setattr(Session, "rollback", _noop)
    return tables


def test_morning_brief_is_returned_from_postgres_when_a_brief_exists(monkeypatch):
    brief = _fake_brief_row()
    action = _fake_action_row(brief_id=brief.id, label="Database-sourced action", done=True)
    _install_fake_db(monkeypatch, briefs=[brief], actions=[action])

    response = client.get("/morning-brief")
    assert response.status_code == 200
    data = response.json()

    assert data["executiveSummary"] == brief.executive_summary
    assert data["meta"]["headline"] == brief.headline
    assert data["meta"]["id"] == str(brief.id)
    assert data["topPriorities"][0]["id"] == "db_pri_1"
    assert data["criticalRisks"][0]["id"] == "db_risk_1"
    assert data["clientsNeedingAttention"][0]["id"] == "db_cli_1"
    assert data["recommendedDelegation"][0]["id"] == "db_del_1"
    assert data["closing"]["question"] == "Database-sourced question?"

    assert len(data["actionChecklist"]) == 1
    assert data["actionChecklist"][0]["id"] == str(action.id)
    assert data["actionChecklist"][0]["done"] is True


def test_morning_brief_falls_back_and_persists_when_none_exists(monkeypatch):
    tables = _install_fake_db(monkeypatch, briefs=[], actions=[])

    response = client.get("/morning-brief")
    assert response.status_code == 200
    data = response.json()

    # Served from demo_data...
    assert data["executiveSummary"] == demo_data.EXECUTIVE_SUMMARY_TEXT
    assert data["meta"]["headline"] == demo_data.BRIEF_META["headline"]

    # ...and persisted, so the next request finds a real row instead of
    # generating one again.
    assert len(tables[MorningBrief]) == 1
    assert len(tables[BriefAction]) == len(demo_data.ACTION_CHECKLIST)
    assert data["meta"]["id"] == str(tables[MorningBrief][0].id)


def test_morning_brief_falls_back_when_the_database_is_unreachable(monkeypatch):
    tables = _install_fake_db(monkeypatch, raise_on_query=True)

    response = client.get("/morning-brief")
    assert response.status_code == 200
    data = response.json()

    assert data["executiveSummary"] == demo_data.EXECUTIVE_SUMMARY_TEXT
    # Persistence isn't possible either when the database is unreachable —
    # this is the pre-migration, mock-only response (stable mock ids).
    assert data["actionChecklist"][0]["id"] == demo_data.ACTION_CHECKLIST[0]["id"]
    assert tables[MorningBrief] == []


def test_regenerate_creates_and_persists_a_brief_when_none_exists(monkeypatch):
    tables = _install_fake_db(monkeypatch, briefs=[], actions=[])

    response = client.post("/morning-brief/regenerate")
    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["generatedLabel"] == "just now"
    assert len(tables[MorningBrief]) == 1
    assert len(tables[BriefAction]) == len(demo_data.ACTION_CHECKLIST)


def test_regenerate_replaces_content_but_preserves_checklist_progress(monkeypatch):
    brief = _fake_brief_row(headline="Yesterday's stale headline")
    # `chk_1` defaults to `done=False` in `demo_data.ACTION_CHECKLIST` — if
    # `regenerate()` incorrectly reset the checklist, this would flip back.
    action = _fake_action_row(brief_id=brief.id, label="Set the Meridian walk-away price", done=True)
    _install_fake_db(monkeypatch, briefs=[brief], actions=[action])

    response = client.post("/morning-brief/regenerate")
    assert response.status_code == 200
    data = response.json()

    # Report content is refreshed from the current generator...
    assert data["meta"]["headline"] == demo_data.BRIEF_META["headline"]
    assert data["meta"]["headline"] != "Yesterday's stale headline"

    # ...but existing checklist progress is left exactly as it was.
    assert len(data["actionChecklist"]) == 1
    assert data["actionChecklist"][0]["done"] is True
    assert data["actionChecklist"][0]["id"] == str(action.id)


def test_checklist_item_persists_to_postgres(monkeypatch):
    brief = _fake_brief_row()
    action = _fake_action_row(brief_id=brief.id, done=False)
    _install_fake_db(monkeypatch, briefs=[brief], actions=[action])

    response = client.patch(f"/morning-brief/checklist/{action.id}", json={"done": True})
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(action.id)
    assert data["done"] is True

    # The underlying row itself was mutated, not just the response shape.
    assert action.done is True
    assert action.completed_at is not None


def test_checklist_item_can_be_unmarked_and_persists(monkeypatch):
    brief = _fake_brief_row()
    action = _fake_action_row(brief_id=brief.id, done=True, completed_at=datetime.now(timezone.utc))
    _install_fake_db(monkeypatch, briefs=[brief], actions=[action])

    response = client.patch(f"/morning-brief/checklist/{action.id}", json={"done": False})
    assert response.status_code == 200
    assert response.json()["done"] is False
    assert action.done is False
    assert action.completed_at is None


def test_unknown_checklist_item_with_a_valid_uuid_returns_404(monkeypatch):
    _install_fake_db(monkeypatch, briefs=[], actions=[])

    response = client.patch(f"/morning-brief/checklist/{uuid4()}", json={"done": True})
    assert response.status_code == 404
