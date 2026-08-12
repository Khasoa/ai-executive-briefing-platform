"""Phase 2.5 — OpenAI integration (fully mocked; no network, no live DB)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.openai import (
    OpenAIBadResponse,
    OpenAIClient,
    OpenAINotConfigured,
    OpenAIRateLimit,
    OpenAITimeout,
    OpenAIUnavailable,
)
from app.models import AskReport, BriefAction, Email, Meeting, MorningBrief, User
from app.services import demo_data
from app.services.ai_service import AIService
from app.services.ask_service import AskService
from app.services.demo_user import DEMO_USER, DEMO_USER_FALLBACK_ID
from app.services.inbox_service import InboxService
from app.services.meeting_service import MeetingService
from app.services.morning_brief_service import MorningBriefService


def _clear_settings() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings():
    _clear_settings()
    yield
    _clear_settings()


def _demo_user(**overrides) -> User:
    data = dict(
        id=DEMO_USER_FALLBACK_ID,
        **DEMO_USER,
        hashed_password="!",
    )
    data.update(overrides)
    return User(**data)


class FakeOpenAIClient:
    def __init__(self, payloads: dict[str, dict] | None = None, error: Exception | None = None):
        self.payloads = payloads or {}
        self.error = error
        self.calls: list[str] = []

    def generate_json(self, *, system, user, schema_name, schema, model=None):
        self.calls.append(schema_name)
        if self.error is not None:
            raise self.error
        if schema_name not in self.payloads:
            raise OpenAIBadResponse(f"no fixture for {schema_name}")
        return self.payloads[schema_name]


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _install_fake_db(monkeypatch, tables: dict[type, list]):
    def _query(self, model, *args, **kwargs):
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


def _stub_context_lists(monkeypatch):
    """Avoid nested DB reads while AIService builds prompts."""
    monkeypatch.setattr(
        "app.services.meeting_service.MeetingService.list_meetings",
        lambda self: [],
    )
    monkeypatch.setattr(
        "app.services.inbox_service.InboxService.list_emails",
        lambda self: [],
    )
    monkeypatch.setattr(
        "app.services.crm_service.CRMService.list_opportunities",
        lambda self: [],
    )
    monkeypatch.setattr(
        "app.services.integration_service.IntegrationService.list_integrations",
        lambda self: [],
    )


MORNING_PAYLOAD = {
    "headline": "AI headline for today.",
    "executive_summary": "AI executive summary.",
    "confidence": "high",
    "sources": ["Gmail", "Google Calendar"],
    "priorities": [
        {
            "id": "pri_ai",
            "rank": 1,
            "title": "AI priority",
            "detail": "Detail",
            "urgency": "high",
            "owner": "Lydia",
            "source": "OpenAI",
        }
    ],
    "risks": [
        {
            "id": "risk_ai",
            "title": "AI risk",
            "detail": "Detail",
            "severity": "medium",
            "impact": "Impact",
            "mitigation": "Mitigate",
            "source": "Gmail",
        }
    ],
    "clients": [
        {
            "id": "cli_ai",
            "company": "Acme",
            "stage": "Negotiation",
            "value": "$100K",
            "lastContact": "Today",
            "reason": "Reason",
            "recommendedAction": "Call",
            "severity": "high",
        }
    ],
    "focus": {
        "headline": "Focus",
        "rationale": "Why",
        "blocks": [
            {
                "id": "blk_1",
                "start": "09:00",
                "end": "10:00",
                "label": "Prep",
                "reason": "Ready",
                "kind": "deep-work",
            }
        ],
    },
    "delegation": [
        {
            "id": "del_ai",
            "task": "Draft note",
            "assignee": "Sam",
            "assigneeRole": "EA",
            "reason": "Bandwidth",
            "effort": "20 min saved",
        }
    ],
    "closing": {
        "question": "What matters?",
        "answer": "Protect the renewal.",
        "bullets": ["One"],
    },
    "checklist": [
        {
            "label": "Decide price",
            "category": "Decision",
            "due": "Before 11:00",
            "done": False,
        }
    ],
}

MEETING_PAYLOAD = {
    "executiveSummary": "Renewal negotiation.",
    "talkingPoints": ["Hold price", "Trade term"],
    "negotiationStrategy": "Anchor on migration cost.",
    "risks": [{"title": "Discount spiral", "detail": "Sets Q4 precedent", "severity": "high"}],
    "questionsToAsk": ["What is the competitor quote?"],
    "followUpRecommendations": ["Send term sheet same day"],
    "prepReason": "AI prep ready.",
}

EMAIL_PAYLOAD = {
    "summary": "Vendor asks for a security questionnaire answer.",
    "importance": "high",
    "actionItems": ["Reply to item 4.7"],
    "followUpSuggestion": "Here is the answer to 4.7…",
}

ASK_PAYLOAD = {
    "summary": "Prioritise the renewal.",
    "confidence": "high",
    "sections": [
        {
            "id": "sec_1",
            "title": "Do first",
            "type": "ranked",
            "items": [{"title": "Set walk-away", "detail": "Before 11:00", "meta": "$480K"}],
            "body": None,
        }
    ],
    "citations": [{"source": "GoHighLevel", "detail": "1 deal", "count": 1}],
    "followUps": ["Prepare me for today's meetings."],
}


# -- OpenAIClient ------------------------------------------------------------


def test_openai_client_missing_key():
    client = OpenAIClient()
    client.api_key = ""
    with pytest.raises(OpenAINotConfigured):
        client.generate_json(
            system="s",
            user="u",
            schema_name="x",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
        )


def test_openai_client_timeout(monkeypatch):
    client = OpenAIClient()
    client.api_key = "sk-test"

    def _raise(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx, "post", _raise)
    with pytest.raises(OpenAITimeout):
        client.generate_json(
            system="s",
            user="u",
            schema_name="x",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
        )


def test_openai_client_rate_limit(monkeypatch):
    client = OpenAIClient()
    client.api_key = "sk-test"

    class _Resp:
        status_code = 429

        def json(self):
            return {}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(OpenAIRateLimit):
        client.generate_json(
            system="s",
            user="u",
            schema_name="x",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
        )


def test_openai_client_unavailable(monkeypatch):
    client = OpenAIClient()
    client.api_key = "sk-test"

    class _Resp:
        status_code = 503

        def json(self):
            return {}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(OpenAIUnavailable):
        client.generate_json(
            system="s",
            user="u",
            schema_name="x",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
        )


def test_openai_client_malformed_json(monkeypatch):
    client = OpenAIClient()
    client.api_key = "sk-test"

    class _Resp:
        status_code = 200

        def json(self):
            return {"output_text": "not-json{"}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(OpenAIBadResponse):
        client.generate_json(
            system="s",
            user="u",
            schema_name="x",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
        )


def test_openai_client_success_parses_output_text(monkeypatch):
    client = OpenAIClient()
    client.api_key = "sk-test"

    class _Resp:
        status_code = 200

        def json(self):
            return {"output_text": '{"ok": true}'}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    assert client.generate_json(
        system="s",
        user="u",
        schema_name="x",
        schema={"type": "object", "properties": {}, "additionalProperties": False},
    ) == {"ok": True}


# -- AIService ---------------------------------------------------------------


def test_ai_service_failover_on_provider_errors(monkeypatch):
    _stub_context_lists(monkeypatch)
    user = _demo_user()
    db = Session()
    for err in (
        OpenAINotConfigured("no key"),
        OpenAITimeout("t"),
        OpenAIRateLimit("r"),
        OpenAIUnavailable("u"),
        OpenAIBadResponse("b"),
    ):
        service = AIService(db, user, client=FakeOpenAIClient(error=err))
        assert service.generate_morning_brief_content() is None
        assert service.generate_meeting_prep({"title": "x"}) is None
        assert service.generate_email_summary({"subject": "x"}) is None
        assert service.answer_question("What should I prioritize today?") is None


def test_ai_service_successful_generation(monkeypatch):
    _stub_context_lists(monkeypatch)
    _install_fake_db(monkeypatch, {User: [_demo_user()]})
    user = _demo_user()
    db = Session()
    fake = FakeOpenAIClient(
        {
            "morning_brief": MORNING_PAYLOAD,
            "meeting_prep": MEETING_PAYLOAD,
            "email_summary": EMAIL_PAYLOAD,
            "ask_report": ASK_PAYLOAD,
        }
    )
    service = AIService(db, user, client=fake)

    brief = service.generate_morning_brief_content()
    assert brief is not None
    assert brief["headline"] == "AI headline for today."
    assert "OpenAI" in brief["sources"]

    prep = service.generate_meeting_prep({"title": "Call"})
    assert prep is not None
    assert "Hold price" in prep["talkingPoints"]

    email_ai = service.generate_email_summary({"subject": "Q"})
    assert email_ai is not None
    assert "Action items:" in email_ai["summary"]

    ask = service.answer_question("What should I prioritize today?")
    assert ask is not None
    assert ask["confidence"] == "high"
    assert fake.calls == [
        "morning_brief",
        "meeting_prep",
        "email_summary",
        "ask_report",
    ]


def test_json_validation_rejects_incomplete_morning_brief(monkeypatch):
    _stub_context_lists(monkeypatch)
    _install_fake_db(monkeypatch, {User: [_demo_user()]})
    service = AIService(Session(), _demo_user(), client=FakeOpenAIClient({"morning_brief": {"headline": "only"}}))
    assert service.generate_morning_brief_content() is None


# -- Morning Brief -----------------------------------------------------------


def test_morning_brief_uses_ai_and_caches(monkeypatch):
    user = _demo_user()
    tables = _install_fake_db(
        monkeypatch,
        {
            User: [user],
            MorningBrief: [],
            BriefAction: [],
        },
    )
    _stub_context_lists(monkeypatch)
    fake = FakeOpenAIClient({"morning_brief": MORNING_PAYLOAD})
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    service = MorningBriefService(Session(), user)
    first = service.get_brief()
    assert first.meta.headline == "AI headline for today."
    assert first.executiveSummary == "AI executive summary."
    assert len(fake.calls) == 1
    assert len(tables[MorningBrief]) == 1

    second = service.get_brief()
    assert second.meta.headline == "AI headline for today."
    assert len(fake.calls) == 1  # cached row

    third = service.regenerate()
    assert third.meta.headline == "AI headline for today."
    assert len(fake.calls) == 2


def test_morning_brief_failover_to_curated(monkeypatch):
    user = _demo_user()
    tables = _install_fake_db(
        monkeypatch,
        {User: [user], MorningBrief: [], BriefAction: []},
    )
    _stub_context_lists(monkeypatch)
    fake = FakeOpenAIClient(error=OpenAIUnavailable("down"))
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    response = MorningBriefService(Session(), user).get_brief()
    assert response.meta.headline == demo_data.BRIEF_META["headline"]
    assert response.executiveSummary == demo_data.EXECUTIVE_SUMMARY_TEXT
    assert len(tables[MorningBrief]) == 1


# -- Meeting prep ------------------------------------------------------------


def test_meeting_prep_generation_and_manual_preservation(monkeypatch):
    user = _demo_user()
    # Midday UTC keeps the event on "today" for Europe/Athens demo timezone.
    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    meeting = Meeting(
        id=uuid4(),
        user_id=user.id,
        title="Meridian renewal",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        type="client",
        location="Zoom",
        prep_status="needs-prep",
        prep_reason="Needs prep",
        attendees=[{"name": "Alex", "role": "CFO", "company": "Meridian", "avatar": "A"}],
        agenda=["Pricing"],
        company={
            "name": "Meridian Labs",
            "industry": "Bio",
            "size": "200",
            "relationship": "Customer",
            "background": "Renewal",
        },
        intelligence={},
        sources=["Google Calendar"],
    )
    _install_fake_db(monkeypatch, {User: [user], Meeting: [meeting], Email: []})
    monkeypatch.setattr(
        "app.services.crm_service.CRMService.list_opportunities",
        lambda self: [],
    )
    fake = FakeOpenAIClient({"meeting_prep": MEETING_PAYLOAD})
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    schema = MeetingService(Session(), user).get_meeting(str(meeting.id))
    assert schema.talkingPoints == ["Hold price", "Trade term"]
    assert schema.prepStatus == "ready"
    assert len(fake.calls) == 1

    meeting.intelligence = {
        "preparationNotes": ["Human note"],
        "talkingPoints": ["Human point"],
        "recommendedQuestions": [],
        "risks": [],
        "manuallyEdited": True,
    }
    schema2 = MeetingService(Session(), user).get_meeting(str(meeting.id))
    assert schema2.preparationNotes == ["Human note"]
    assert len(fake.calls) == 1


# -- Email summaries ---------------------------------------------------------


def test_email_summary_generation_and_manual_preservation(monkeypatch):
    user = _demo_user()
    row = Email(
        id=uuid4(),
        user_id=user.id,
        category="needs-reply",
        subject="Security questionnaire",
        sender={
            "name": "Priya",
            "email": "priya@example.com",
            "avatar": "P",
            "company": "Pinnacle",
        },
        ai_summary="",
        priority="medium",
        suggested_response="",
        reading_time="1 min",
        thread_count=1,
        unread=True,
        labels=["INBOX"],
        received_at=datetime.now(timezone.utc),
    )
    _install_fake_db(monkeypatch, {User: [user], Email: [row]})
    fake = FakeOpenAIClient({"email_summary": EMAIL_PAYLOAD})
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    schema = InboxService(Session(), user).get_email(str(row.id))
    assert "Vendor asks" in schema.aiSummary
    assert schema.priority == "high"
    assert "4.7" in schema.suggestedResponse
    assert len(fake.calls) == 1

    InboxService(Session(), user).get_email(str(row.id))
    assert len(fake.calls) == 1

    row.ai_summary = "Manual summary"
    row.suggested_response = "Manual draft"
    schema2 = InboxService(Session(), user).get_email(str(row.id))
    assert schema2.aiSummary == "Manual summary"
    assert schema2.suggestedResponse == "Manual draft"
    assert len(fake.calls) == 1


# -- Ask ---------------------------------------------------------------------


def test_ask_ai_answer_and_history(monkeypatch):
    user = _demo_user()
    tables = _install_fake_db(monkeypatch, {User: [user], AskReport: []})
    _stub_context_lists(monkeypatch)
    fake = FakeOpenAIClient({"ask_report": ASK_PAYLOAD})
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    report = AskService(Session(), user).answer("What should I prioritize today?")
    assert report.summary == "Prioritise the renewal."
    assert len(fake.calls) == 1
    assert len(tables[AskReport]) == 1
    assert tables[AskReport][0].question == "What should I prioritize today?"

    workspace = AskService(Session(), user).get_workspace()
    assert any(r.question == "What should I prioritize today?" for r in workspace.recent)


def test_ask_failover_to_curated(monkeypatch):
    user = _demo_user()
    _install_fake_db(monkeypatch, {User: [user], AskReport: []})
    _stub_context_lists(monkeypatch)
    fake = FakeOpenAIClient(error=OpenAIRateLimit("429"))
    original_init = AIService.__init__

    def _init(self, db, user, client=None):
        original_init(self, db, user, client=fake)

    monkeypatch.setattr(AIService, "__init__", _init)

    report = AskService(Session(), user).answer("What should I prioritize today?")
    assert "Meridian" in report.summary
    assert "ask_report" in fake.calls
