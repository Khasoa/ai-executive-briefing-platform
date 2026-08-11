"""Weekly Email Digest — AI, cache, fallback, user scoping (mocked OpenAI)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Email,
    Meeting,
    Opportunity,
    RefreshToken,
    User,
    WeeklyDigest,
    WorkItem,
)
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.demo_data import USER as DEMO_USER
from app.services.weekly_digest_service import MIN_SIGNALS_FOR_AI, WeeklyDigestService

client = TestClient(app)
MIN_EMAILS_FOR_AI = MIN_SIGNALS_FOR_AI


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(WeeklyDigest).filter(WeeklyDigest.user_id == user.id).delete()
        db.query(Email).filter(Email.user_id == user.id).delete()
        db.query(Meeting).filter(Meeting.user_id == user.id).delete()
        db.query(Opportunity).filter(Opportunity.user_id == user.id).delete()
        db.query(WorkItem).filter(WorkItem.user_id == user.id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="Digest",
            full_name="Digest User",
            role="CEO",
            company="Test Co",
            avatar="DU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _token(user_id) -> str:
    db = SessionLocal()
    try:
        return AuthService(db).issue_tokens(db.get(User, user_id)).accessToken
    finally:
        db.close()


def _add_emails(user_id, count: int, *, days_ago_start: int = 0) -> list[str]:
    db = SessionLocal()
    ids = []
    try:
        now = datetime.now(timezone.utc)
        for i in range(count):
            received = now - timedelta(days=days_ago_start, hours=i)
            row = Email(
                user_id=user_id,
                category="needs-reply" if i % 2 == 0 else "informational",
                subject=f"Thread {i}: decision needed" if i % 3 == 0 else f"Update {i}",
                sender={"name": f"Sender {i}", "email": f"s{i}@example.com"},
                ai_summary=f"Summary of thread {i}",
                priority="high" if i < 2 else "medium",
                suggested_response="",
                reading_time="1 min",
                thread_count=1,
                unread=i % 2 == 0,
                labels=["Work"],
                received_at=received,
            )
            db.add(row)
            db.flush()
            ids.append(str(row.id))
        db.commit()
        return ids
    finally:
        db.close()


def _item(title: str, source: str = "Gmail", kind: str = "fact") -> dict:
    return {
        "id": title[:8],
        "title": title,
        "detail": "Details",
        "source": source,
        "emailIds": [],
        "kind": kind,
    }


AI_PAYLOAD = {
    "week": "Aug 2 – 8, 2026",
    "headline": "AI digest headline",
    "summary": "AI summary of the week.",
    "week_summary": "AI summary of the week.",
    "important_conversations": [_item("Important thread")],
    "decisions_and_approvals": [],
    "follow_ups": [_item("Follow up")],
    "unresolved_items": [],
    "notable_activity": [],
    "carry_into_next_week": [_item("Carry item")],
    "next_week_outlook": {
        "upcoming_meetings": [_item("Board prep", "Google Calendar")],
        "upcoming_deadlines": [],
        "overdue_work": [],
        "crm_attention": [],
        "email_follow_ups": [],
        "work_items": [],
        "carry_forward": [_item("Carry item")],
        "recommended_priorities": [_item("Focus Monday", "OpenAI", "recommendation")],
        "risks_and_watchouts": [],
        "workload_signals": [],
    },
    "planning_note": "Plan Monday carefully.",
    "confidence": "high",
    "sources": ["Gmail"],
}


def test_weekly_digest_empty_inbox_curated():
    email = f"wd-empty-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        token = _token(user.id)
        response = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["emailCount"] == 0
        assert data["generatedBy"] == "curated"
        assert data["importantConversations"] == []
        assert "Quiet" in data["headline"] or "No synced" in data["summary"]
        assert "nextWeekOutlook" in data
    finally:
        _cleanup(email)


def test_weekly_digest_retrieves_only_last_7_days(monkeypatch):
    email = f"wd-win-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, 4, days_ago_start=0)
        # Old mail outside window
        db = SessionLocal()
        try:
            db.add(
                Email(
                    user_id=user.id,
                    category="informational",
                    subject="Ancient thread",
                    sender={"name": "Old", "email": "old@example.com"},
                    ai_summary="Should not appear",
                    priority="low",
                    received_at=datetime.now(timezone.utc) - timedelta(days=20),
                )
            )
            db.commit()
        finally:
            db.close()

        monkeypatch.setattr(
            AIService,
            "generate_weekly_digest",
            lambda self, ctx: None,
        )
        db = SessionLocal()
        try:
            svc = WeeklyDigestService(db, db.get(User, user.id))
            start, end = svc._current_week_bounds()
            emails = svc._emails_in_window(start, end)
            subjects = {e["subject"] for e in emails}
            assert "Ancient thread" not in subjects
            assert len(emails) == 4
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_weekly_digest_ai_success_and_sources(monkeypatch):
    email = f"wd-ai-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, MIN_EMAILS_FOR_AI + 1)
        monkeypatch.setattr(
            AIService,
            "generate_weekly_digest",
            lambda self, ctx: AIService._normalise_weekly_digest(AI_PAYLOAD),
        )
        token = _token(user.id)
        response = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["generatedBy"] == "openai"
        assert data["headline"] == "AI digest headline"
        assert "Gmail" in data["sources"]
        assert "OpenAI" in data["sources"]
        assert data["importantConversations"][0]["source"] == "Gmail"
        assert data["planningNote"]
    finally:
        _cleanup(email)


def test_weekly_digest_ai_failure_fallback(monkeypatch):
    email = f"wd-fail-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, 5)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        response = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["generatedBy"] == "curated"
        assert data["emailCount"] == 5
        assert data["importantConversations"] or data["followUps"]
    finally:
        _cleanup(email)


def test_weekly_digest_insufficient_emails_skips_ai(monkeypatch):
    email = f"wd-few-{uuid.uuid4().hex[:10]}@example.com"
    called = {"n": 0}

    def _should_not_run(self, ctx):
        called["n"] += 1
        return None

    try:
        user = _seed_user(email)
        _add_emails(user.id, 2)
        monkeypatch.setattr(AIService, "generate_weekly_digest", _should_not_run)
        token = _token(user.id)
        response = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["generatedBy"] == "curated"
        assert called["n"] == 0
    finally:
        _cleanup(email)


def test_weekly_digest_cache_and_regenerate(monkeypatch):
    email = f"wd-cache-{uuid.uuid4().hex[:10]}@example.com"
    calls = {"n": 0}

    def _ai(self, ctx):
        calls["n"] += 1
        payload = dict(AI_PAYLOAD)
        payload["headline"] = f"AI call {calls['n']}"
        return AIService._normalise_weekly_digest(payload)

    try:
        user = _seed_user(email)
        _add_emails(user.id, 4)
        monkeypatch.setattr(AIService, "generate_weekly_digest", _ai)
        token = _token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        first = client.get("/weekly-digest", headers=headers).json()
        second = client.get("/weekly-digest", headers=headers).json()
        assert first["id"] == second["id"]
        assert first["headline"] == second["headline"]
        assert calls["n"] == 1

        third = client.post("/weekly-digest/regenerate", headers=headers).json()
        assert calls["n"] == 2
        assert third["headline"] == "AI call 2"
        assert third["id"] == first["id"]
    finally:
        _cleanup(email)


def test_weekly_digest_user_scoping():
    a = f"wd-a-{uuid.uuid4().hex[:10]}@example.com"
    b = f"wd-b-{uuid.uuid4().hex[:10]}@example.com"
    try:
        ua = _seed_user(a)
        ub = _seed_user(b)
        _add_emails(ua.id, 4)
        _add_emails(ub.id, 4)

        db = SessionLocal()
        try:
            start = datetime.now(timezone.utc).date() - timedelta(days=6)
            end = datetime.now(timezone.utc).date()
            db.add(
                WeeklyDigest(
                    user_id=ua.id,
                    week_start=start,
                    week_end=end,
                    headline="User A digest",
                    summary="A only",
                    planning_note="",
                    generated_by="curated",
                    sources=["Gmail"],
                    email_count=4,
                    sections={"important_conversations": [], "follow_ups": []},
                )
            )
            db.commit()
        finally:
            db.close()

        token_b = _token(ub.id)
        # Force B to generate its own (no shared row)
        response = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert response.status_code == 200
        assert response.json()["headline"] != "User A digest"

        db = SessionLocal()
        try:
            rows = db.query(WeeklyDigest).filter(WeeklyDigest.user_id == ub.id).all()
            assert len(rows) == 1
            assert all(r.user_id == ub.id for r in rows)
        finally:
            db.close()
    finally:
        _cleanup(a)
        _cleanup(b)


def test_weekly_digest_normalise_rejects_bad_schema():
    assert AIService._normalise_weekly_digest({"headline": "x"}) is None
    good = AIService._normalise_weekly_digest(AI_PAYLOAD)
    assert good is not None
    assert good["sources"][-1] == "OpenAI" or "OpenAI" in good["sources"]


def test_weekly_digest_scoped_to_bearer_user():
    email = f"wd-scope-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, 3)
        token = _token(user.id)
        response = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        digest_id = response.json()["id"]
        db = SessionLocal()
        try:
            row = db.query(WeeklyDigest).filter(WeeklyDigest.id == uuid.UUID(digest_id)).one()
            assert row.user_id == user.id
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_weekly_digest_real_gmail_intelligence(monkeypatch):
    email = f"wd-gmail-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, 4)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert data["emailCount"] == 4
        assert data["dataCoverage"]["sourcesWithData"] == ["Gmail"]
        assert data["importantConversations"] or data["followUps"]
        assert all(
            item["source"] == "Gmail"
            for item in data["importantConversations"] + data["followUps"]
        )
    finally:
        _cleanup(email)


def test_weekly_digest_calendar_next_week_meetings(monkeypatch):
    email = f"wd-cal-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            db.add(
                Meeting(
                    user_id=user.id,
                    title="Board sync",
                    starts_at=now + timedelta(days=2),
                    ends_at=now + timedelta(days=2, hours=1),
                    type="external",
                    location="Zoom",
                    prep_status="ready",
                    prep_reason="Review deck",
                    attendees=[],
                    agenda=[],
                    company={"name": "Acme"},
                    intelligence={"executiveSummary": "Prep renewal talking points"},
                    sources=["Google Calendar"],
                )
            )
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        meetings = data["nextWeekOutlook"]["upcomingMeetings"]
        assert any("Board sync" in m["title"] for m in meetings)
        assert "Google Calendar" in data["dataCoverage"]["sourcesWithData"]
    finally:
        _cleanup(email)


def test_weekly_digest_work_items_deadlines(monkeypatch):
    email = f"wd-work-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="monday",
                    external_id="monday:dead-1",
                    title="Ship pricing page",
                    status="In Progress",
                    priority="high",
                    due_at=now + timedelta(days=3),
                    sources=["monday.com"],
                )
            )
            db.add(
                WorkItem(
                    user_id=user.id,
                    provider="clickup",
                    external_id="clickup:ov-1",
                    title="Overdue docs",
                    status="Open",
                    priority="urgent",
                    due_at=now - timedelta(days=2),
                    sources=["ClickUp"],
                )
            )
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        outlook = data["nextWeekOutlook"]
        assert outlook["upcomingDeadlines"] or outlook["overdueWork"]
        sources = data["dataCoverage"]["sourcesWithData"]
        assert "monday.com" in sources or "ClickUp" in sources
    finally:
        _cleanup(email)


def test_weekly_digest_crm_attention(monkeypatch):
    email = f"wd-crm-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            db.add(
                Opportunity(
                    user_id=user.id,
                    company="Risk Corp",
                    stage="Negotiation",
                    value=50000,
                    probability=40,
                    owner="Pat",
                    risk_level="high",
                    recommended_action="Call champion this week",
                    ai_summary="Deal stalled 12 days",
                )
            )
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert data["nextWeekOutlook"]["crmAttention"]
        assert "GoHighLevel" in data["dataCoverage"]["sourcesWithData"]
        assert data["nextWeekOutlook"]["crmAttention"][0]["kind"] == "fact"
    finally:
        _cleanup(email)


def test_weekly_digest_combined_sources(monkeypatch):
    email = f"wd-multi-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        _add_emails(user.id, 2)
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            db.add(
                Meeting(
                    user_id=user.id,
                    title="Customer QBR",
                    starts_at=now + timedelta(days=1),
                    ends_at=now + timedelta(days=1, hours=1),
                    type="external",
                    location="Meet",
                    company={},
                    intelligence={},
                    sources=["Google Calendar"],
                )
            )
            db.add(
                Opportunity(
                    user_id=user.id,
                    company="Multi Co",
                    stage="Proposal",
                    value=12000,
                    probability=55,
                    owner="A",
                    risk_level="critical",
                    recommended_action="Send revised SOW",
                )
            )
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        sources = set(data["dataCoverage"]["sourcesWithData"])
        assert "Gmail" in sources
        assert "Google Calendar" in sources
        assert "GoHighLevel" in sources
        assert data["nextWeekOutlook"]["upcomingMeetings"]
        assert data["nextWeekOutlook"]["crmAttention"]
    finally:
        _cleanup(email)


def test_weekly_digest_insufficient_gmail_no_hallucination(monkeypatch):
    email = f"wd-meta-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            for i in range(4):
                db.add(
                    Email(
                        user_id=user.id,
                        category="informational",
                        subject=f"Metadata only {i}",
                        sender={"name": "A", "email": "a@example.com"},
                        ai_summary="",
                        priority="medium",
                        received_at=now - timedelta(hours=i),
                    )
                )
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        note = data["dataCoverage"]["emailNote"]
        assert "limited" in note.lower() or "metadata" in note.lower()
        blob = " ".join(
            item["detail"]
            for item in (data["importantConversations"] + data["followUps"] + data["notableActivity"])
        ).lower()
        assert "body" in blob or "metadata" in blob or "limited" in blob
        assert "invented paragraph" not in blob
    finally:
        _cleanup(email)


def test_weekly_digest_non_demo_isolation_from_demo_identity(monkeypatch):
    email = f"wd-iso-{uuid.uuid4().hex[:10]}@example.com"
    try:
        user = _seed_user(email)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get(
            "/weekly-digest", headers={"Authorization": f"Bearer {token}"}
        ).json()
        assert DEMO_USER["fullName"] not in data["headline"]
        assert "Meridian" not in data["summary"]
        assert data["emailCount"] == 0
        assert not data["importantConversations"]
    finally:
        _cleanup(email)
