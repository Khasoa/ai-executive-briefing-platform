"""Gmail → Email incremental sync."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.token_crypto import encrypt_secret
from app.db.session import SessionLocal
from app.integrations.gmail import GmailHistoryExpired, GmailHistoryPage, GmailListPage
from app.main import app
from app.models import Email, Integration, RefreshToken, SyncEvent, User
from app.services.gmail_sync_service import GmailSyncService
from app.services.inbox_service import InboxService

client = TestClient(app)


def _cleanup_email(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return
        db.query(Email).filter(Email.user_id == user.id).delete()
        integrations = db.query(Integration).filter(Integration.user_id == user.id).all()
        for row in integrations:
            db.query(SyncEvent).filter(SyncEvent.integration_id == row.id).delete()
            db.delete(row)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_google_user(email: str, *, with_gmail_scope: bool = True) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email,
            hashed_password=None,
            name="Mail",
            full_name="Mail User",
            role="CEO",
            company="Test",
            avatar="MU",
            timezone="UTC",
            is_active=True,
            preferences={},
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        scopes = [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        if with_gmail_scope:
            scopes.append("https://www.googleapis.com/auth/gmail.readonly")

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
                        "access_token": encrypt_secret("ya29.gmail-access", settings),
                        "refresh_token": encrypt_secret("1//gmail-refresh", settings),
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                        "scope": " ".join(scopes),
                        "token_type": "Bearer",
                    },
                    "profile": {"sub": f"sub-{uuid.uuid4().hex[:8]}", "email": email},
                    "gmail": {},
                },
                connected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _gmail_message(
    message_id: str,
    *,
    subject: str = "Hello",
    from_header: str = "Ada Lovelace <ada@example.com>",
    label_ids: list[str] | None = None,
    snippet: str = "Short preview text",
    thread_id: str = "thread_1",
) -> dict:
    return {
        "id": message_id,
        "threadId": thread_id,
        "labelIds": label_ids or ["INBOX", "UNREAD"],
        "snippet": snippet,
        "internalDate": "1723000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": from_header},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Thu, 7 Aug 2026 10:00:00 +0000"},
            ]
        },
    }


def test_full_and_incremental_gmail_sync(monkeypatch):
    email = f"gmail-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        messages = {
            "msg_1": _gmail_message("msg_1", subject="First", label_ids=["INBOX", "UNREAD", "IMPORTANT"]),
            "msg_2": _gmail_message("msg_2", subject="Second", label_ids=["INBOX"]),
        }

        monkeypatch.setattr(
            "app.services.gmail_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.gmail-access",
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_labels",
            lambda self: {
                "INBOX": "INBOX",
                "UNREAD": "UNREAD",
                "IMPORTANT": "IMPORTANT",
                "Label_42": "Clients",
            },
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_profile",
            lambda self: {"historyId": "100", "emailAddress": email},
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_messages",
            lambda self, **kwargs: GmailListPage(
                message_refs=[
                    {"id": "msg_1", "threadId": "thread_1"},
                    {"id": "msg_2", "threadId": "thread_2"},
                ]
            ),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_message",
            lambda self, message_id, **kwargs: messages[message_id],
        )

        db = SessionLocal()
        try:
            service = GmailSyncService(db)
            first = service.sync_user(user, reason="manual")
            assert first["upserted"] == 2

            row = (
                db.query(Email)
                .filter(Email.user_id == user.id, Email.external_id == "gmail:msg_1")
                .one()
            )
            assert row.subject == "First"
            assert row.sender["email"] == "ada@example.com"
            assert "IMPORTANT" in row.labels or "IMPORTANT" in [l.upper() for l in row.labels]
            assert row.ai_summary == ""  # left empty for AIService fill
            assert row.suggested_response == ""
            assert row.thread_id == "thread_1"

            # Preserve local AI fields on update; refresh labels from Gmail.
            row.ai_summary = "Locally written note"
            row.suggested_response = "Draft reply"
            row.priority = "high"
            db.commit()

            messages["msg_1"] = _gmail_message(
                "msg_1",
                subject="First updated",
                label_ids=["INBOX", "IMPORTANT", "Label_42"],
                snippet="Ignored because summary already set",
            )

            monkeypatch.setattr(
                "app.integrations.gmail.GmailClient.list_history",
                lambda self, **kwargs: GmailHistoryPage(
                    messages_added=[],
                    messages_deleted=[],
                    labels_changed=["msg_1"],
                    history_id="101",
                ),
            )
            monkeypatch.setattr(
                "app.integrations.gmail.GmailClient.get_profile",
                lambda self: {"historyId": "101", "emailAddress": email},
            )

            second = service.sync_user(user, reason="manual")
            assert second["upserted"] == 1
            db.refresh(row)
            assert row.subject == "First updated"
            assert row.ai_summary == "Locally written note"
            assert row.suggested_response == "Draft reply"
            assert "Clients" in row.labels

            # Delete via history
            monkeypatch.setattr(
                "app.integrations.gmail.GmailClient.list_history",
                lambda self, **kwargs: GmailHistoryPage(
                    messages_deleted=["msg_2"],
                    history_id="102",
                ),
            )
            monkeypatch.setattr(
                "app.integrations.gmail.GmailClient.get_profile",
                lambda self: {"historyId": "102", "emailAddress": email},
            )
            third = service.sync_user(user, reason="manual")
            assert third["deleted"] == 1
            assert (
                db.query(Email)
                .filter(Email.user_id == user.id, Email.external_id == "gmail:msg_2")
                .first()
            ) is None

            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert google.config["gmail"]["history_id"] == "102"

            gmail_row = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "gmail")
                .one()
            )
            assert gmail_row.status == "connected"

            listed = InboxService(db, user).list_emails()
            assert any(e["subject"] == "First updated" for e in listed)
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_expired_history_triggers_full_resync(monkeypatch):
    email = f"hist-{uuid.uuid4().hex[:10]}@example.com"
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
            config["gmail"] = {"history_id": "stale"}
            google.config = config
            db.commit()
        finally:
            db.close()

        state = {"phase": "stale"}

        def fake_history(self, **kwargs):
            if state["phase"] == "stale":
                state["phase"] = "full"
                raise GmailHistoryExpired()
            raise AssertionError("history should not be called after expiry")

        monkeypatch.setattr(
            "app.services.gmail_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.gmail-access",
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_labels",
            lambda self: {"INBOX": "INBOX"},
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_history",
            fake_history,
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_messages",
            lambda self, **kwargs: GmailListPage(
                message_refs=[{"id": "msg_r", "threadId": "t"}]
            ),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_message",
            lambda self, message_id, **kwargs: _gmail_message(message_id),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_profile",
            lambda self: {"historyId": "200", "emailAddress": email},
        )

        db = SessionLocal()
        try:
            counts = GmailSyncService(db).sync_user(user)
            assert counts["upserted"] == 1
            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            assert google.config["gmail"]["history_id"] == "200"
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_gmail_webhook_triggers_sync(monkeypatch):
    email = f"push-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        monkeypatch.setattr(
            "app.services.gmail_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.gmail-access",
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_labels",
            lambda self: {"INBOX": "INBOX"},
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_history",
            lambda self, **kwargs: GmailHistoryPage(
                messages_added=["msg_push"],
                history_id="9",
            ),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_messages",
            lambda self, **kwargs: GmailListPage(
                message_refs=[{"id": "msg_push", "threadId": "t"}]
            ),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_message",
            lambda self, message_id, **kwargs: _gmail_message(message_id, subject="Pushed"),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_profile",
            lambda self: {"historyId": "9", "emailAddress": email},
        )

        payload = {
            "message": {
                "data": base64.b64encode(
                    json.dumps({"emailAddress": email, "historyId": 8}).encode()
                ).decode()
            }
        }
        response = client.post("/webhooks/google/gmail", json=payload)
        assert response.status_code == 204

        db = SessionLocal()
        try:
            assert (
                db.query(Email)
                .filter(Email.user_id == user.id, Email.external_id == "gmail:msg_push")
                .count()
            ) == 1
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_sync_requires_gmail_scope():
    email = f"noscope-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email, with_gmail_scope=False)
    try:
        db = SessionLocal()
        try:
            try:
                GmailSyncService(db).sync_user(user)
                assert False, "expected 409"
            except Exception as exc:
                assert getattr(exc, "status_code", None) == 409
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_idempotent_external_id_no_duplicates(monkeypatch):
    email = f"dup-{uuid.uuid4().hex[:10]}@example.com"
    user = _seed_google_user(email)
    try:
        monkeypatch.setattr(
            "app.services.gmail_sync_service.OAuthService.refresh_provider_access_token",
            lambda self, user, provider: "ya29.gmail-access",
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_labels",
            lambda self: {"INBOX": "INBOX"},
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.list_messages",
            lambda self, **kwargs: GmailListPage(
                message_refs=[{"id": "same", "threadId": "t"}]
            ),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_message",
            lambda self, message_id, **kwargs: _gmail_message(message_id),
        )
        monkeypatch.setattr(
            "app.integrations.gmail.GmailClient.get_profile",
            lambda self: {"historyId": "1", "emailAddress": email},
        )

        db = SessionLocal()
        try:
            service = GmailSyncService(db)
            service.sync_user(user)
            # Clear history so next sync is full again
            google = (
                db.query(Integration)
                .filter(Integration.user_id == user.id, Integration.provider == "google")
                .one()
            )
            config = dict(google.config or {})
            config["gmail"] = {}
            google.config = config
            db.commit()

            service.sync_user(user)
            assert (
                db.query(Email)
                .filter(Email.user_id == user.id, Email.external_id == "gmail:same")
                .count()
            ) == 1
        finally:
            db.close()
    finally:
        _cleanup_email(email)


def test_demo_inbox_unchanged_without_gmail_sync():
    response = client.get("/inbox")
    assert response.status_code == 200
    assert response.json()["emails"]
