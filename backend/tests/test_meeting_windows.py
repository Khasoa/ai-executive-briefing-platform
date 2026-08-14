"""Timezone-aware meeting classification and Today's Focus prep gates."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import Email, Meeting, RefreshToken, User, WeeklyDigest
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.meeting_intelligence import MeetingIntelligenceService
from app.services.meeting_windows import (
    classify_meeting_at,
    prep_recommended_for_meeting,
    prep_recommended_for_window,
)
from app.services.morning_brief_service import MorningBriefService
from app.services.overview_service import OverviewService

client = TestClient(app)


def _cleanup(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(WeeklyDigest).filter(WeeklyDigest.user_id == user.id).delete()
        from app.models import BriefAction, MorningBrief

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


def _seed_user(email: str, *, tz: str = "UTC") -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=None,
            name="Meet",
            full_name="Meet User",
            role="CEO",
            company="Test",
            avatar="MU",
            timezone=tz,
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


def _add_meeting(
    user_id,
    *,
    starts_at: datetime,
    title: str = "Sync",
    prep_status: str = "needs-prep",
    company: dict | None = None,
    attendees: list | None = None,
) -> str:
    db = SessionLocal()
    try:
        meeting = Meeting(
            user_id=user_id,
            external_id=f"primary:evt_{uuid.uuid4().hex[:12]}",
            title=title,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            type="internal",
            location="Zoom",
            prep_status=prep_status,
            prep_reason="Imported",
            attendees=attendees or [],
            agenda=[],
            company=company or {},
            intelligence={},
            sources=["Google Calendar"],
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return str(meeting.id)
    finally:
        db.close()


def _user(user_id) -> User:
    db = SessionLocal()
    try:
        return db.get(User, user_id)
    finally:
        db.close()


def test_classify_meeting_windows_relative_to_now():
    user = User(timezone="UTC")
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)  # Tuesday
    assert classify_meeting_at(now, user, now=now) == "today"
    assert classify_meeting_at(now + timedelta(days=1), user, now=now) == "tomorrow"
    assert classify_meeting_at(now + timedelta(days=3), user, now=now) == "this_week"  # Fri
    assert classify_meeting_at(now + timedelta(days=10), user, now=now) == "this_month"
    assert classify_meeting_at(now + timedelta(days=40), user, now=now) == "later"
    assert classify_meeting_at(now - timedelta(days=1), user, now=now) == "past"


def test_prep_recommended_only_for_today():
    assert prep_recommended_for_window("today", "needs-prep") is True
    assert prep_recommended_for_window("today", "ready") is False
    assert prep_recommended_for_window("this_week", "needs-prep") is False
    assert prep_recommended_for_window("later", "needs-prep") is False


def test_prep_recommended_rolling_24h_horizon():
    user = User(
        id=uuid.uuid4(),
        email="prep@example.com",
        hashed_password="!",
        name="P",
        full_name="P",
        role="CEO",
        company="T",
        avatar="P",
        timezone="UTC",
        is_active=True,
        preferences={},
    )
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    assert prep_recommended_for_meeting(
        now + timedelta(minutes=30), "needs-prep", user, now=now
    )
    assert prep_recommended_for_meeting(
        now + timedelta(hours=6), "needs-prep", user, now=now
    )
    assert prep_recommended_for_meeting(
        now + timedelta(hours=23), "needs-prep", user, now=now
    )
    # Inclusive far boundary
    assert prep_recommended_for_meeting(
        now + timedelta(hours=24), "needs-prep", user, now=now
    )
    assert not prep_recommended_for_meeting(
        now + timedelta(hours=25), "needs-prep", user, now=now
    )
    assert not prep_recommended_for_meeting(
        now + timedelta(days=3), "needs-prep", user, now=now
    )
    # Tomorrow morning within 24h from noon
    assert prep_recommended_for_meeting(
        now + timedelta(hours=18), "needs-prep", user, now=now
    )
    # September / October — not eligible
    assert not prep_recommended_for_meeting(
        datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc),
        "needs-prep",
        user,
        now=now,
    )
    assert not prep_recommended_for_meeting(
        datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc),
        "needs-prep",
        user,
        now=now,
    )
    # Past
    assert not prep_recommended_for_meeting(
        now - timedelta(hours=1), "needs-prep", user, now=now
    )
    # Already prepared
    assert not prep_recommended_for_meeting(
        now + timedelta(hours=2), "ready", user, now=now
    )


def test_prep_horizon_respects_user_timezone_africa_nairobi():
    user = User(
        id=uuid.uuid4(),
        email="nairobi@example.com",
        hashed_password="!",
        name="N",
        full_name="N",
        role="CEO",
        company="T",
        avatar="N",
        timezone="Africa/Nairobi",
        is_active=True,
        preferences={},
    )
    # 22:00 UTC = 01:00 next day Nairobi (UTC+3)
    now = datetime(2026, 8, 14, 22, 0, tzinfo=timezone.utc)
    # 20 hours later = still within 24h
    assert prep_recommended_for_meeting(
        now + timedelta(hours=20), "needs-prep", user, now=now
    )
    assert not prep_recommended_for_meeting(
        now + timedelta(hours=26), "needs-prep", user, now=now
    )


def test_timezone_midnight_boundary_athens():
    """23:30 UTC Aug 10 is already Aug 11 in Europe/Athens (+3)."""
    user = User(timezone="Europe/Athens")
    now_utc = datetime(2026, 8, 10, 22, 0, tzinfo=timezone.utc)  # 01:00 Athens Aug 11
    local_morning = datetime(2026, 8, 11, 9, 0, tzinfo=ZoneInfo("Europe/Athens"))
    assert classify_meeting_at(local_morning, user, now=now_utc) == "today"
    still_prev_day = datetime(2026, 8, 10, 20, 0, tzinfo=ZoneInfo("Europe/Athens"))
    assert classify_meeting_at(still_prev_day, user, now=now_utc) == "past"


def test_api_windows_and_counts():
    email = f"mw-api-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(user.id, starts_at=now + timedelta(hours=2), title="Today board")
        _add_meeting(user.id, starts_at=now + timedelta(days=1), title="Tomorrow 1:1")
        _add_meeting(user.id, starts_at=now + timedelta(days=3), title="Later this week")
        _add_meeting(user.id, starts_at=now + timedelta(days=12), title="Later this month")
        _add_meeting(user.id, starts_at=now + timedelta(days=40), title="Next month kickoff")
        _add_meeting(user.id, starts_at=now - timedelta(days=2), title="Past retro")
        _add_meeting(
            user.id,
            starts_at=now + timedelta(days=28),
            title="Monthly writers call",
        )

        token = _token(user.id)
        data = client.get("/meetings", headers={"Authorization": f"Bearer {token}"}).json()
        assert data["todayCount"] == 1
        assert data["needsPreparationToday"] == 1
        assert data["meetingCount"] == 1
        assert len(data["windows"]["today"]) == 1
        assert data["windows"]["today"][0]["title"] == "Today board"
        assert data["windows"]["today"][0]["prepRecommended"] is True
        assert data["windows"]["today"][0]["relativeLabel"]
        titles_weekish = {m["title"] for m in data["windows"]["tomorrow"] + data["windows"]["thisWeek"]}
        assert "Tomorrow 1:1" in titles_weekish or "Tomorrow 1:1" in {
            m["title"] for m in data["windows"]["tomorrow"]
        }
        later_titles = {m["title"] for m in data["windows"]["later"] + data["windows"]["thisMonth"]}
        assert "Next month kickoff" in later_titles or "Monthly writers call" in later_titles
        past_titles = {m["title"] for m in data["windows"]["past"]}
        assert "Past retro" in past_titles
        # Prep uses a rolling 24h horizon — tomorrow within 24h may be eligible;
        # meetings beyond that must not be flagged.
        horizon = now + timedelta(hours=24)
        for section in ("tomorrow", "thisWeek", "thisMonth", "later"):
            for m in data["windows"][section]:
                starts = m.get("startsAt")
                if not starts:
                    assert m["prepRecommended"] is False
                    continue
                start_dt = datetime.fromisoformat(starts.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                within = now <= start_dt <= horizon
                assert m["prepRecommended"] is within, m["title"]
        for m in data["windows"]["later"] + data["windows"]["thisMonth"]:
            if m["title"] in ("Next month kickoff", "Monthly writers call", "Later this month"):
                assert m["prepRecommended"] is False
        # Ensure far-future September/October-class meetings stay out of prep.
        assert all(
            m["prepRecommended"] is False for m in data["windows"]["later"]
        )
    finally:
        _cleanup(email)


def test_today_meeting_with_related_email_context():
    email = f"mw-rel-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(
            user.id,
            starts_at=now + timedelta(hours=3),
            title="Acme renewal review",
            company={"name": "Acme Corp"},
            attendees=[{"name": "Pat", "email": "pat@acme.example.com"}],
        )
        db = SessionLocal()
        try:
            db.add(
                Email(
                    user_id=user.id,
                    category="informational",
                    subject="Acme Corp contract draft",
                    sender={"name": "Pat", "email": "pat@acme.example.com"},
                    ai_summary="Draft attached for renewal.",
                    priority="medium",
                    unread=True,
                    labels=["INBOX"],
                    received_at=now - timedelta(days=1),
                )
            )
            db.commit()
            u = db.get(User, user.id)
            intel = MeetingIntelligenceService(db, u)
            today = intel.todays_meetings()
            assert len(today) == 1
            ctx = intel.build_prep_context(today[0])
            assert ctx["relatedEmailMatches"]
            assert "Available context" in ctx["contextAvailability"]["contextNote"]
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_today_meeting_without_supporting_context():
    email = f"mw-empty-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(user.id, starts_at=now + timedelta(hours=1), title="Internal stand-up")
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            ctx = MeetingIntelligenceService(db, u).build_prep_context(
                MeetingIntelligenceService(db, u).todays_meetings()[0]
            )
            assert "Limited context available" in ctx["contextAvailability"]["contextNote"]
            assert ctx["relatedEmailMatches"] == []
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_future_meeting_not_in_todays_focus_or_prepare():
    email = f"mw-focus-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(user.id, starts_at=now + timedelta(days=20), title="Monthly all-hands")
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            ov = OverviewService(db, u).get_overview()
            titles = [f.title for f in ov.focus]
            assert "Monthly all-hands" not in titles
            prep = ov.executiveSummary.meetingsToPrepare
            assert all(p.title != "Monthly all-hands" for p in prep)
            focus_items = MeetingIntelligenceService(db, u).focus_items_for_today()
            assert focus_items == []
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_future_meeting_does_not_trigger_prepare_today_in_brief(monkeypatch):
    email = f"mw-brief-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(user.id, starts_at=now + timedelta(days=25), title="Quarterly offsite")
        # Ordinary non-urgent email so brief is not "no activity".
        db = SessionLocal()
        try:
            db.add(
                Email(
                    user_id=user.id,
                    category="informational",
                    subject="Weekly newsletter",
                    sender={"name": "News", "email": "n@example.com"},
                    ai_summary="",
                    priority="medium",
                    unread=True,
                    labels=["INBOX"],
                    received_at=now - timedelta(hours=2),
                )
            )
            db.commit()
        finally:
            db.close()

        monkeypatch.setattr(AIService, "generate_morning_brief_content", lambda self: None)
        db = SessionLocal()
        try:
            brief = MorningBriefService(db, db.get(User, user.id)).get_brief()
            text = (brief.executiveSummary or "").lower()
            assert "no synced email or calendar activity" not in text
            assert "requiring your attention or decisions today" not in text
            # Future meeting should not be framed as today's prep queue alone.
            assert "quarterly offsite" not in " ".join(
                (m.title or "").lower() for m in brief.meetings
            ) or "planning" in text or "no meetings today" in text or "later" in text
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_meaningful_activity_not_treated_as_no_activity(monkeypatch):
    email = f"mw-act-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            for i in range(4):
                db.add(
                    Email(
                        user_id=user.id,
                        category="informational",
                        subject=f"Update {i}",
                        sender={"name": f"S{i}", "email": f"s{i}@ex.com"},
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
        monkeypatch.setattr(AIService, "generate_morning_brief_content", lambda self: None)
        db = SessionLocal()
        try:
            brief = MorningBriefService(db, db.get(User, user.id)).get_brief()
            text = (brief.executiveSummary or "").lower()
            assert "waiting on synced activity" not in text
            assert "no meetings, emails" not in text
            assert brief.importantEmails
        finally:
            db.close()
    finally:
        _cleanup(email)


def test_recurring_monthly_classified_as_later_or_month_not_today():
    email = f"mw-rec-{uuid.uuid4().hex[:8]}@example.com"
    try:
        user = _seed_user(email)
        now = datetime.now(timezone.utc)
        _add_meeting(
            user.id,
            starts_at=now + timedelta(days=21),
            title="Monthly product council",
        )
        db = SessionLocal()
        try:
            u = db.get(User, user.id)
            meetings = MeetingIntelligenceService(db, u).load_classified_meetings()
            m = meetings[0]
            assert m["window"] in ("this_week", "this_month", "later")
            assert m["window"] != "today"
            assert m["prepRecommended"] is False
        finally:
            db.close()
    finally:
        _cleanup(email)
