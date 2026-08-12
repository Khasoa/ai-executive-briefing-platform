"""Intelligence layer: digest/overview/brief use real activity, not urgency-only."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import Email, Meeting, RefreshToken, User, WeeklyDigest
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.morning_brief_service import MorningBriefService
from app.services.overview_service import OverviewService
from app.services.weekly_digest_service import WeeklyDigestService

client = TestClient(app)


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(WeeklyDigest).filter(WeeklyDigest.user_id == user.id).delete()
        from app.models import MorningBrief, BriefAction

        for brief in db.query(MorningBrief).filter(MorningBrief.user_id == user.id).all():
            db.query(BriefAction).filter(BriefAction.brief_id == brief.id).delete()
            db.delete(brief)
        db.query(Email).filter(Email.user_id == user.id).delete()
        db.query(Meeting).filter(Meeting.user_id == user.id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_user(email: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=None,
            name="Intel",
            full_name="Intel User",
            role="CEO",
            company="Test",
            avatar="IU",
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


def _add_routine_emails(user_id, count: int = 5) -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for i in range(count):
            db.add(
                Email(
                    user_id=user_id,
                    category="informational",
                    subject=f"Routine update {i} from newsletter",
                    sender={"name": f"Sender{i}", "email": f"s{i}@news.example.com"},
                    ai_summary="",
                    priority="medium",
                    unread=True,
                    labels=["INBOX"],
                    received_at=now - timedelta(hours=i + 1),
                )
            )
        db.commit()
    finally:
        db.close()


def _add_meeting(user_id, *, days_ahead: int = 3, title: str = "Planning sync", external_id: str | None = None) -> None:
    db = SessionLocal()
    try:
        start = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        db.add(
            Meeting(
                user_id=user_id,
                external_id=external_id or f"primary:evt_{uuid.uuid4().hex[:12]}",
                title=title,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                type="call",
                location="",
                prep_status="needs-prep",
                prep_reason="Imported",
                attendees=[],
                agenda="",
                company={},
                intelligence={},
                sources=["Google Calendar"],
            )
        )
        db.commit()
    finally:
        db.close()


def test_weekly_digest_not_empty_with_routine_emails_in_window(monkeypatch):
    email = f"intel-wd-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        _add_routine_emails(user.id, 6)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"}).json()
        assert data["emailCount"] >= 6
        assert "Quiet week" not in data["headline"]
        assert data["dataCoverage"]["sourcesWithData"]
        assert "Gmail" in data["dataCoverage"]["sourcesWithData"]
        assert data["importantConversations"] or data["followUps"] or data["notableActivity"]
    finally:
        _cleanup(email)


def test_weekly_digest_includes_meetings_and_outlook(monkeypatch):
    email = f"intel-mtg-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        _add_routine_emails(user.id, 3)
        _add_meeting(user.id, days_ahead=-2, title="Past standup")
        _add_meeting(user.id, days_ahead=4, title="Next week review")
        _add_meeting(user.id, days_ahead=20, title="Monthly writers call")
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"}).json()
        assert data["emailCount"] >= 3
        outlook = data["nextWeekOutlook"]
        titles = [m["title"] for m in outlook.get("upcomingMeetings") or []]
        assert "Next week review" in titles or any("writers" in t.lower() for t in titles)
        notable = [n["title"] for n in data.get("notableActivity") or []]
        assert "Past standup" in notable or "Next week review" in titles
    finally:
        _cleanup(email)


def test_stale_quiet_digest_cache_refreshes_when_data_arrives(monkeypatch):
    email = f"intel-stale-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        db = SessionLocal()
        try:
            svc = WeeklyDigestService(db, db.get(User, user.id))
            ws, we = svc._current_week_bounds()
            db.add(
                WeeklyDigest(
                    user_id=user.id,
                    week_start=ws,
                    week_end=we,
                    headline=f"Quiet week · {ws}",
                    summary="No synced activity was found",
                    planning_note="",
                    confidence="low",
                    generated_by="curated",
                    sources=[],
                    email_count=0,
                    sections={"important_conversations": [], "data_coverage": {"emailCount": 0}},
                    generated_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        _add_routine_emails(user.id, 4)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        token = _token(user.id)
        data = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"}).json()
        assert data["emailCount"] >= 4
        assert "Quiet week" not in data["headline"]
    finally:
        _cleanup(email)


def test_genuinely_empty_user_still_quiet():
    email = f"intel-empty-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        token = _token(user.id)
        data = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"}).json()
        assert data["emailCount"] == 0
        assert "Quiet" in data["headline"] or "No synced" in data["summary"]
    finally:
        _cleanup(email)


def test_digest_user_isolation(monkeypatch):
    a = f"intel-a-{uuid.uuid4().hex[:8]}@example.com"
    b = f"intel-b-{uuid.uuid4().hex[:8]}@example.com"
    try:
        ua = _seed_user(a)
        ub = _seed_user(b)
        _add_routine_emails(ua.id, 5)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        data_b = client.get(
            "/weekly-digest",
            headers={"Authorization": f"Bearer {_token(ub.id)}"},
        ).json()
        assert data_b["emailCount"] == 0
        data_a = client.get(
            "/weekly-digest",
            headers={"Authorization": f"Bearer {_token(ua.id)}"},
        ).json()
        assert data_a["emailCount"] >= 5
    finally:
        _cleanup(a)
        _cleanup(b)


def test_ai_unavailable_still_shows_deterministic_activity(monkeypatch):
    email = f"intel-ai-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        _add_routine_emails(user.id, 5)
        monkeypatch.setattr(AIService, "generate_weekly_digest", lambda self, ctx: None)
        monkeypatch.setattr(AIService, "generate_morning_brief_content", lambda self: None)
        token = _token(user.id)
        digest = client.get("/weekly-digest", headers={"Authorization": f"Bearer {token}"}).json()
        assert digest["generatedBy"] == "curated"
        assert digest["emailCount"] >= 5
        brief = client.get("/morning-brief", headers={"Authorization": f"Bearer {token}"}).json()
        assert brief["executiveSummary"]
        assert "no meetings, emails, CRM" not in brief["executiveSummary"].lower()
    finally:
        _cleanup(email)


def test_overview_focus_and_overnight_from_gmail(monkeypatch):
    email = f"intel-ov-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        _add_routine_emails(user.id, 4)
        _add_meeting(user.id, days_ahead=2, title="Product review")
        db = SessionLocal()
        try:
            ov = OverviewService(db, db.get(User, user.id)).get_overview()
            assert len(ov.focus) >= 1
            assert len(ov.activity) >= 1
            assert any(a.type == "email" for a in ov.activity)
            # Future meeting must not populate Today's Focus merely by existing.
            assert "Product review" not in [f.title for f in ov.focus]
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_morning_brief_situational_not_nothing(monkeypatch):
    email = f"intel-mb-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        _add_routine_emails(user.id, 5)
        monkeypatch.setattr(AIService, "generate_morning_brief_content", lambda self: None)
        db = SessionLocal()
        try:
            brief = MorningBriefService(db, db.get(User, user.id)).get_brief()
            text = (brief.executiveSummary or "").lower()
            assert "requiring your attention or decisions today" not in text
            assert brief.importantEmails
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_duplicate_external_ids_not_created_same_provider_id():
    """Upsert is idempotent per external_id; distinct Google IDs may share title/time."""
    email = f"intel-dup-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        start = datetime.now(timezone.utc) + timedelta(days=1)
        db = SessionLocal()
        try:
            for ext in ("primary:abc123", "primary:abc123"):
                existing = (
                    db.query(Meeting)
                    .filter(Meeting.user_id == user.id, Meeting.external_id == ext)
                    .first()
                )
                if existing is None:
                    db.add(
                        Meeting(
                            user_id=user.id,
                            external_id=ext,
                            title="Hack Week",
                            starts_at=start,
                            ends_at=start + timedelta(hours=1),
                            type="call",
                            location="",
                            prep_status="needs-prep",
                            prep_reason="",
                            attendees=[],
                            agenda="",
                            company={},
                            intelligence={},
                            sources=["Google Calendar"],
                        )
                    )
                db.commit()
            count = (
                db.query(Meeting)
                .filter(Meeting.user_id == user.id, Meeting.external_id == "primary:abc123")
                .count()
            )
            assert count == 1

            # Distinct provider IDs with same title/time are allowed (not an upsert bug).
            db.add(
                Meeting(
                    user_id=user.id,
                    external_id="primary:xyz999",
                    title="Hack Week",
                    starts_at=start,
                    ends_at=start + timedelta(hours=1),
                    type="call",
                    location="",
                    prep_status="needs-prep",
                    prep_reason="",
                    attendees=[],
                    agenda="",
                    company={},
                    intelligence={},
                    sources=["Google Calendar"],
                )
            )
            db.commit()
            assert (
                db.query(Meeting)
                .filter(Meeting.user_id == user.id, Meeting.title == "Hack Week")
                .count()
                == 2
            )
            # Digest presentation dedupes title+start.
            svc = WeeklyDigestService(db, db.get(User, user.id))
            meetings = [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "startsAt": m.starts_at.isoformat(),
                }
                for m in db.query(Meeting).filter(Meeting.user_id == user.id).all()
            ]
            assert len(svc._dedupe_meetings(meetings)) == 1
        finally:
            db.close()
    finally:
        _cleanup(email)
