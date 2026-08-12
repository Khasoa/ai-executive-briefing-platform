"""POST /webhooks/n8n/email-follow-up — executive email triage via AIService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas.email_follow_up import EmailFollowUpRequest
from app.services.ai_service import AIService
from app.services.demo_user import DEMO_USER, DEMO_USER_FALLBACK_ID
from app.services.email_follow_up_intelligence_service import EmailFollowUpIntelligenceService
from app.models import User

client = TestClient(app)
SECRET = "test-n8n-secret-email-follow-up"


def _enable_secret(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", SECRET)
    get_settings.cache_clear()


def _headers():
    return {"X-Briefly-N8N-Secret": SECRET}


def _demo_user() -> User:
    return User(id=DEMO_USER_FALLBACK_ID, **DEMO_USER, hashed_password="!")


ACTION_PAYLOAD = {
    "requires_action": True,
    "priority": "high",
    "category": "approval_request",
    "action": "Approve the Q3 budget revision",
    "deadline": "Friday 17:00",
    "reason": "Sender explicitly asks for approval before Friday.",
    "suggested_response": "Thanks — I'll review the revision and confirm by Friday.",
    "confidence": 0.91,
}

PROMO_PAYLOAD = {
    "requires_action": False,
    "priority": "low",
    "category": "promotional",
    "action": None,
    "deadline": None,
    "reason": "Marketing discount offer with no executive decision requested.",
    "suggested_response": None,
    "confidence": 0.88,
}

MEETING_PAYLOAD = {
    "requires_action": True,
    "priority": "medium",
    "category": "meeting_request",
    "action": "Confirm or decline the proposed meeting time",
    "deadline": None,
    "reason": "Sender requests a meeting and asks for availability.",
    "suggested_response": "Happy to meet — Thursday 10:00 works on my side.",
    "confidence": 0.84,
}


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_action_required_email(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(
        AIService,
        "generate_email_follow_up",
        lambda self, ctx: ACTION_PAYLOAD,
    )
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_action_1",
            "thread_id": "thr_1",
            "sender": "cfo@company.com",
            "subject": "Please approve Q3 budget revision",
            "received_at": "2026-08-11T09:00:00Z",
            "body": "Can you approve the attached Q3 budget revision by Friday 17:00?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_action"] is True
    assert data["priority"] == "high"
    assert data["action"]
    assert data["deadline"] == "Friday 17:00"


def test_non_action_promotional_email(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(
        AIService,
        "generate_email_follow_up",
        lambda self, ctx: PROMO_PAYLOAD,
    )
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_promo_1",
            "thread_id": None,
            "sender": "deals@shop.example.com",
            "subject": "Get 50% off something tasty",
            "received_at": None,
            "body": "Limited time — shop now and save 50%!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_action"] is False
    assert data["priority"] == "low"
    assert data["category"] == "promotional"
    assert data["action"] is None
    assert data["deadline"] is None


def test_high_priority_email(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(
        AIService,
        "generate_email_follow_up",
        lambda self, ctx: ACTION_PAYLOAD,
    )
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_hp",
            "thread_id": "t",
            "sender": "investor@fund.com",
            "subject": "Decision needed on term sheet",
            "received_at": "2026-08-11T12:00:00Z",
            "body": "We need your decision on the term sheet today.",
        },
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "high"
    assert response.json()["requires_action"] is True


def test_explicit_deadline_extraction(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(
        AIService,
        "generate_email_follow_up",
        lambda self, ctx: ACTION_PAYLOAD,
    )
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    data = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_dl",
            "thread_id": None,
            "sender": "ops@company.com",
            "subject": "Approve by Friday",
            "received_at": None,
            "body": "Please approve before Friday 17:00.",
        },
    ).json()
    assert data["deadline"] == "Friday 17:00"
    assert "Friday" in data["reason"] or data["requires_action"]


def test_malformed_ai_response_returns_api_error(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(AIService, "generate_email_follow_up", lambda self, ctx: None)
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_bad",
            "thread_id": None,
            "sender": "a@b.com",
            "subject": "Hello",
            "received_at": None,
            "body": "Test",
        },
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "OpenAI" not in detail
    assert "api key" not in detail.lower()
    assert "unavailable" in detail.lower()


def test_promotional_classified_as_non_action(monkeypatch):
    """Normalisation + service path for promo — requires_action stays false."""
    user = _demo_user()
    ai = MagicMock()
    ai.generate_email_follow_up.return_value = PROMO_PAYLOAD
    service = EmailFollowUpIntelligenceService(MagicMock(), user, ai=ai)
    result = service.analyze(
        EmailFollowUpRequest(
            message_id="m1",
            thread_id=None,
            sender="news@mailchimp.com",
            subject="INVEST IN NAIROBI REAL ESTATE.",
            received_at=None,
            body="Great opportunity — unsubscribe anytime.",
        )
    )
    assert result.requires_action is False
    assert result.category == "promotional"
    # Ensure body was passed to AI but service does not echo it.
    call_ctx = ai.generate_email_follow_up.call_args[0][0]
    assert "body" in call_ctx
    assert "message_id" in call_ctx


def test_meeting_request_classified_as_action_required(monkeypatch):
    _enable_secret(monkeypatch)
    monkeypatch.setattr(
        AIService,
        "generate_email_follow_up",
        lambda self, ctx: MEETING_PAYLOAD,
    )
    monkeypatch.setattr(
        "app.services.orchestration_service.get_or_create_demo_user",
        lambda db: _demo_user(),
    )
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers=_headers(),
        json={
            "message_id": "msg_meet",
            "thread_id": "thr_m",
            "sender": "partner@client.com",
            "subject": "Can we meet Thursday?",
            "received_at": "2026-08-11T08:00:00Z",
            "body": "Would you be free Thursday 10:00 for a 30-minute sync?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_action"] is True
    assert data["category"] == "meeting_request"
    assert data["suggested_response"]


def test_email_follow_up_rejects_bad_secret(monkeypatch):
    _enable_secret(monkeypatch)
    response = client.post(
        "/webhooks/n8n/email-follow-up",
        headers={"X-Briefly-N8N-Secret": "wrong"},
        json={
            "message_id": "m",
            "thread_id": None,
            "sender": "a@b.com",
            "subject": "Hi",
            "body": "x",
        },
    )
    assert response.status_code == 401


def test_normalise_rejects_malformed_json():
    assert AIService._normalise_email_follow_up({"requires_action": True}) is None
    assert AIService._normalise_email_follow_up(
        {
            "requires_action": True,
            "priority": "urgent",
            "category": "x",
            "reason": "y",
            "confidence": 0.5,
        }
    ) is None
    good = AIService._normalise_email_follow_up(ACTION_PAYLOAD)
    assert good is not None
    assert good["priority"] == "high"
