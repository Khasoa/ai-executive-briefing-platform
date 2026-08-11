"""Google Calendar → Meeting incremental sync."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.google_calendar import (
    CalendarEventPage,
    GoogleCalendarSyncTokenExpired,
)
from app.main import app
from app.models import Integration, Meeting, RefreshToken, SyncEvent, User
from app.services.calendar_sync_service import CalendarSyncService
from app.services.meeting_service import MeetingService

client = TestClient(app)


def _cleanup_email(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(Meeting).filter(Meeting.user_id == user.id).delete()
        integrations = (
            db.query(Integration).filter(Integration.user_id == user.id).all()
        )
        for row in integrations:
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_google_user(email: str, *, with_calendar_scope: bool = True) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="Cal",
            full_name="Cal User",
            role="CEO",
            company="Test",
            avatar="CU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        scopes = ["openid", "email", "profile"]
        if with_calendar_scope:
            scopes.append("https://www.googleapis.com/auth/calendar.readonly")

        settings = get_settings()
        db.add(
            Integration(
                user_id=user.id,
                provider="google",
                status="connected",
                account=email,
                scopes=scopes,
                config={
                    "oauth": {
                        "access_token": encrypt_secret("ya29.test-access", settings),
                        "refresh_token": encrypt_secret("1//test-refresh", settings),
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                        "scope": " ".join(scopes),
                        "token_type": "Bearer",
                    },
                    "profile": {"sub": f"sub-{uuid.uuid4().hex[:8]}", "email": email},
                    "calendar": {},
                },
                connected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _event(
    event_id: str,
    *,
    summary: str = "Sync Meeting",
    status: str = "confirmed",
    start: str = "2026-08-07T10:00:00Z",
    end: str = "2026-08-07T11:00:00Z",
) -> dict:
    return {
        "id": event_id,
        "status": status,
        "summary": summary,
        "location": "Zoom",
        "description": "Line one\nLine two",
        "htmlLink": "https://calendar.google.com/event?eid=" + event_id,
        "updated": "2026-08-07T09:00:00Z",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "attendees": [
            {
                "email": "guest@example.com",
                "displayName": "Guest Person",
                "organizer": False,
            }
        ],
        "organizer": {"email": "host@example.com", "displayName": "Host Co"},
    }


def test_incremental_sync_upserts_updates_and_deletes(monkeypatch):
    email = f"cal-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        pages = [
            CalendarEventPage(
                events=[_event("evt_1", summary="First Title")],
                next_sync_token="token-1",
            ),
            CalendarEventPage(
                events=[
                    _event("evt_1", summary="Updated Title"),
                    _event("evt_2", summary="Second"),
                ],
                next_sync_token="token-2",
            ),
            CalendarEventPage(
                events=[_event("evt_2", status="cancelled")],
                next_sync_token="token-3",
            ),
        ]
        calls = {"n": 0}

        def fake_list(self, **kwargs):
            page = pages[calls["n"]]
            calls["n"] += 1
            return page

        monkeypatch.setattr(
            "app.services.calendar_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.test-access",
        )
        monkeypatch.setattr(
            "app.integrations.google_calendar.GoogleCalendarClient.list_event_changes",
            fake_list,
        )

        db = SessionLocal()
        try:
            service = CalendarSyncService(db)
            first = service.sync_user(user, reason="manual")
            assert first["upserted"] == 1

            meeting = (
                db.query(Meeting)
                .filter(Meeting.user_id == user.id, Meeting.external_id == "primary:evt_1")
                .one()
            )
            meeting.prep_status = "ready"
            meeting.prep_reason = "Local prep note"
            meeting.intelligence = {
                "relatedEmails": [],
                "preparationNotes": ["Keep me"],
                "talkingPoints": ["Local point"],
                "recommendedQuestions": [],
                "risks": [],
            }
            db.commit()

            second = service.sync_user(user, reason="manual")
            assert second["upserted"] == 2
            db.refresh(meeting)
            assert meeting.title == "Updated Title"
            assert meeting.prep_status == "ready"
            assert meeting.prep_reason == "Local prep note"
            assert meeting.intelligence["preparationNotes"] == ["Keep me"]
            assert meeting.intelligence["talkingPoints"] == ["Local point"]
            assert "Google Calendar" in meeting.sources

            third = service.sync_user(user, reason="manual")
            assert third["deleted"] == 1
            assert (
                db.query(Meeting)
                .filter(Meeting.user_id == user.id, Meeting.external_id == "primary:evt_2")
                .first()
            ) is None

            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert google.config["calendar"]["sync_token"] == "token-3"

            cal_row = (
                db.query(Integration)
                .filter(
                    Integration.user_id == user.id,
                    Integration.provider == "google-calendar",
                )
                .one()
            )
            assert cal_row.status == "connected"

            # MeetingService surfaces synced rows (no demo fallback).
            listed = MeetingService(db, user).list_meetings()
            assert any(m["title"] == "Updated Title" for m in listed)
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_expired_sync_token_triggers_full_resync(monkeypatch):
    email = f"cal410-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        db = SessionLocal()
        try:
            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            config = dict(google.config or {})
            config["calendar"] = {"sync_token": "stale-token"}
            google.config = config
            db.commit()
        finally:
            db.close()

        state = {"phase": "stale"}

        def fake_list(self, **kwargs):
            if state["phase"] == "stale":
                state["phase"] = "full"
                raise GoogleCalendarSyncTokenExpired()
            return CalendarEventPage(
                events=[_event("evt_recover")],
                next_sync_token="fresh-token",
            )

        monkeypatch.setattr(
            "app.services.calendar_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.test-access",
        )
        monkeypatch.setattr(
            "app.integrations.google_calendar.GoogleCalendarClient.list_event_changes",
            fake_list,
        )

        db = SessionLocal()
        try:
            counts = CalendarSyncService(db).sync_user(user)
            assert counts["upserted"] == 1
            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert google.config["calendar"]["sync_token"] == "fresh-token"
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_webhook_triggers_incremental_sync(monkeypatch):
    email = f"hook-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        db = SessionLocal()
        try:
            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            config = dict(google.config or {})
            config["calendar"] = {
                "channel_id": "channel-abc",
                "resource_id": "resource-xyz",
                "sync_token": "tok",
            }
            google.config = config
            db.commit()
        finally:
            db.close()

        monkeypatch.setattr(
            "app.services.calendar_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.test-access",
        )
        monkeypatch.setattr(
            "app.integrations.google_calendar.GoogleCalendarClient.list_event_changes",
            lambda self, **kwargs: CalendarEventPage(
                events=[_event("evt_hook")],
                next_sync_token="tok-2",
            ),
        )

        # Handshake ignored
        handshake = client.post(
            "/webhooks/google/calendar",
            headers={
                "X-Goog-Channel-ID": "channel-abc",
                "X-Goog-Resource-State": "sync",
            },
        )
        assert handshake.status_code == 204

        notify = client.post(
            "/webhooks/google/calendar",
            headers={
                "X-Goog-Channel-ID": "channel-abc",
                "X-Goog-Resource-State": "exists",
                "X-Goog-Resource-ID": "resource-xyz",
            },
        )
        assert notify.status_code == 204

        db = SessionLocal()
        try:
            assert (
                db.query(Meeting)
                .filter(Meeting.user_id == user.id, Meeting.external_id == "primary:evt_hook")
                .count()
            ) == 1
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_sync_requires_calendar_scope():
    email = f"noscope-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email, with_calendar_scope=False)
    try:
        db = SessionLocal()
        try:
            try:
                CalendarSyncService(db).sync_user(user)
                assert False, "expected 409"
            except Exception as exc:
                assert getattr(exc, "status_code", None) == 409
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_demo_meetings_unchanged_without_google_sync():
    response = client.get("/meetings")
    assert response.status_code == 200
    data = response.json()
    assert data["meetingCount"] >= 1
    assert data["todayCount"] >= 1
    assert len(data["windows"]["today"]) >= 1
