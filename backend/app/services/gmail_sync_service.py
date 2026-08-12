"""Synchronize Gmail messages into `Email` rows.

InboxService stays read-only: when synced rows exist for the user they
surface via `list_emails()`; otherwise demo fallback remains. No AI
summaries or suggested responses are generated here.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.gmail import GMAIL_READONLY_SCOPE, GmailClient, GmailHistoryExpired
from app.models import Email, Integration, SyncEvent, User
from app.services.email_classification import classify_from_gmail_metadata
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.gmail_sync")

GOOGLE_PROVIDER = "google"
GMAIL_PROVIDER = "gmail"


class GmailSyncService:
    """Incremental, idempotent Gmail → Email sync (webhook-ready)."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        """Pull Gmail changes for `user` and upsert/delete Email rows.

        Returns ``{"upserted": n, "deleted": n, "pages": n}``.
        """
        google = self._require_google_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, GOOGLE_PROVIDER)
        self._ensure_gmail_scope(google)

        client = GmailClient(access_token, self.settings)
        label_map = client.list_labels()
        gmail_meta = dict((google.config or {}).get("gmail") or {})
        history_id = gmail_meta.get("history_id")

        try:
            if history_id:
                counts = self._sync_incremental(user, client, label_map, str(history_id))
            else:
                counts = self._sync_full(user, client, label_map)
        except GmailHistoryExpired:
            logger.info("Gmail historyId expired for user %s — full resync", user.id)
            gmail_meta.pop("history_id", None)
            self._save_gmail_meta(google, gmail_meta)
            counts = self._sync_full(user, client, label_map)

        self.db.refresh(google)
        gmail_meta = dict((google.config or {}).get("gmail") or {})
        # Always refresh profile historyId after a successful sync.
        profile = client.get_profile()
        if profile.get("historyId") is not None:
            gmail_meta["history_id"] = str(profile["historyId"])
            gmail_meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
            self._save_gmail_meta(google, gmail_meta)

        self._ensure_gmail_integration_row(user, google, gmail_meta, reason)
        return counts

    def handle_pubsub_notification(self, *, email_address: str, history_id: str | None) -> dict[str, int] | None:
        """Process a Gmail Pub/Sub push payload (webhook-ready)."""
        integration = (
            self.db.query(Integration)
            .filter(
                Integration.provider == GOOGLE_PROVIDER,
                Integration.status == "connected",
                Integration.account == email_address.lower(),
            )
            .first()
        )
        if integration is None:
            # Also match gmail UI row account.
            integration = (
                self.db.query(Integration)
                .filter(
                    Integration.provider == GMAIL_PROVIDER,
                    Integration.status == "connected",
                    Integration.account == email_address.lower(),
                )
                .first()
            )
            if integration is None:
                logger.warning("No Google integration for Gmail push %s", email_address)
                return None
            user = self.db.get(User, integration.user_id)
        else:
            user = self.db.get(User, integration.user_id)

        if user is None or not user.is_active:
            return None

        if history_id:
            google = self._require_google_integration(user)
            meta = dict((google.config or {}).get("gmail") or {})
            # Keep the oldest unprocessed cursor if we already have one.
            if not meta.get("history_id"):
                meta["history_id"] = str(history_id)
                self._save_gmail_meta(google, meta)

        return self.sync_user(user, reason="webhook")

    def ensure_watch(self, user: User) -> dict[str, Any] | None:
        """Register Gmail users.watch when a Pub/Sub topic is configured."""
        topic = self.settings.gmail_pubsub_topic.strip()
        if not topic:
            return None

        google = self._require_google_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, GOOGLE_PROVIDER)
        client = GmailClient(access_token, self.settings)
        result = client.register_watch(topic_name=topic, label_ids=["INBOX"])
        gmail_meta = dict((google.config or {}).get("gmail") or {})
        gmail_meta.update(
            {
                "history_id": result.history_id or gmail_meta.get("history_id"),
                "watch_expiration_ms": result.expiration_ms,
                "pubsub_topic": topic,
            }
        )
        self._save_gmail_meta(google, gmail_meta)
        return gmail_meta

    def _sync_full(
        self, user: User, client: GmailClient, label_map: dict[str, str]
    ) -> dict[str, int]:
        upserted = pages = 0
        lookback = self.settings.gmail_sync_lookback_days
        max_messages = self.settings.gmail_sync_max_messages
        query = f"newer_than:{lookback}d"
        page_token = None
        while True:
            page = client.list_messages(query=query, page_token=page_token)
            pages += 1
            for ref in page.message_refs:
                if upserted >= max_messages:
                    self.db.commit()
                    return {"upserted": upserted, "deleted": 0, "pages": pages}
                if self._upsert_message(user, client, ref["id"], label_map):
                    upserted += 1
            page_token = page.next_page_token
            if not page_token:
                break
        self.db.commit()
        return {"upserted": upserted, "deleted": 0, "pages": pages}

    def _sync_incremental(
        self,
        user: User,
        client: GmailClient,
        label_map: dict[str, str],
        history_id: str,
    ) -> dict[str, int]:
        upserted = deleted = pages = 0
        page_token = None
        seen_upsert: set[str] = set()
        seen_delete: set[str] = set()

        while True:
            page = client.list_history(start_history_id=history_id, page_token=page_token)
            pages += 1
            for message_id in page.messages_deleted:
                if message_id in seen_delete:
                    continue
                seen_delete.add(message_id)
                if self._delete_message(user, message_id):
                    deleted += 1
            for message_id in page.messages_added + page.labels_changed:
                if message_id in seen_upsert or message_id in seen_delete:
                    continue
                seen_upsert.add(message_id)
                if self._upsert_message(user, client, message_id, label_map):
                    upserted += 1
            page_token = page.next_page_token
            if not page_token:
                break

        self.db.commit()
        return {"upserted": upserted, "deleted": deleted, "pages": pages}

    def _upsert_message(
        self,
        user: User,
        client: GmailClient,
        message_id: str,
        label_map: dict[str, str],
    ) -> bool:
        try:
            raw = client.get_message(message_id, format="metadata")
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return self._delete_message(user, message_id)
            raise

        external_id = f"gmail:{message_id}"
        existing = (
            self.db.query(Email)
            .filter(Email.user_id == user.id, Email.external_id == external_id)
            .first()
        )

        label_ids = list(raw.get("labelIds") or [])
        labels = _resolve_labels(label_ids, label_map)
        headers = _header_map(raw)
        subject = (headers.get("subject") or "(No subject)").strip()[:500]
        sender = _parse_sender(headers.get("from") or "")
        received_at = _parse_received(raw, headers.get("date"))
        unread = "UNREAD" in label_ids
        thread_id = str(raw.get("threadId") or "") or None
        # Gmail thread size is not on metadata payload; keep existing or 1.
        thread_count = existing.thread_count if existing is not None else 1
        category, priority, _signal = classify_from_gmail_metadata(
            subject=subject,
            sender=sender,
            labels=labels,
            label_ids=label_ids,
            headers=headers,
            prior_meaningful=False,
        )
        # Native Gmail snippet is used only for reading-time estimation.
        # Leave AI fields empty so InboxService / AIService can fill them.
        snippet = (raw.get("snippet") or "").strip()

        if existing is None:
            email = Email(
                user_id=user.id,
                external_id=external_id,
                thread_id=thread_id,
                category=category,
                subject=subject,
                sender=sender,
                ai_summary="",
                priority=priority,
                suggested_response="",
                reading_time=_estimate_reading_time(snippet),
                thread_count=thread_count,
                unread=unread,
                labels=labels,
                received_at=received_at,
            )
            self.db.add(email)
        else:
            existing.thread_id = thread_id
            existing.subject = subject
            existing.sender = sender
            existing.unread = unread
            existing.labels = labels  # provider labels are source of truth
            existing.received_at = received_at or existing.received_at
            # Never overwrite locally filled AI fields on sync.
            if not (existing.suggested_response or "").strip():
                existing.suggested_response = ""
            # Refresh promo/newsletter classification; keep intentional action categories.
            if existing.category in (
                "informational",
                "promotional",
                "newsletter",
                "automated",
                None,
                "",
            ):
                existing.category = category
                if existing.priority in ("medium", "low", None, ""):
                    existing.priority = priority

        self.db.flush()
        return True

    def _delete_message(self, user: User, message_id: str) -> bool:
        external_id = f"gmail:{message_id}"
        existing = (
            self.db.query(Email)
            .filter(Email.user_id == user.id, Email.external_id == external_id)
            .first()
        )
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.flush()
        return True

    def _require_google_integration(self, user: User) -> Integration:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == GOOGLE_PROVIDER,
                Integration.status == "connected",
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google is not connected for this user",
            )
        return row

    def _ensure_gmail_scope(self, google: Integration) -> None:
        scopes = " ".join(google.scopes or [])
        oauth_scope = ((google.config or {}).get("oauth") or {}).get("scope") or ""
        combined = f"{scopes} {oauth_scope}"
        if GMAIL_READONLY_SCOPE not in combined and "gmail.readonly" not in combined:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Gmail permission missing — reconnect Google to grant gmail.readonly"
                ),
            )

    def _save_gmail_meta(self, google: Integration, gmail_meta: dict[str, Any]) -> None:
        config = dict(google.config or {})
        config["gmail"] = gmail_meta
        google.config = config
        google.last_sync_at = datetime.now(timezone.utc)
        google.status = "connected"
        self.db.add(google)
        self.db.commit()

    def _ensure_gmail_integration_row(
        self,
        user: User,
        google: Integration,
        gmail_meta: dict[str, Any],
        reason: str,
    ) -> None:
        row = (
            self.db.query(Integration)
            .filter(Integration.user_id == user.id, Integration.provider == GMAIL_PROVIDER)
            .first()
        )
        now = datetime.now(timezone.utc)
        display = {
            "name": "Gmail",
            "category": "Email",
            "description": "Thread summarisation, prioritisation and suggested responses.",
            "poweredBy": "Gmail API",
            "metrics": [],
            "gmail": gmail_meta,
            "token_provider": GOOGLE_PROVIDER,
        }
        if row is None:
            row = Integration(
                user_id=user.id,
                provider=GMAIL_PROVIDER,
                status="connected",
                account=google.account,
                scopes=[GMAIL_READONLY_SCOPE],
                config=display,
                connected_at=now,
                last_sync_at=now,
            )
            self.db.add(row)
        else:
            prior = dict(row.config or {})
            prior.pop("last_error", None)
            merged = {**prior, **display}
            merged.pop("last_error", None)
            row.status = "connected"
            row.account = google.account
            row.scopes = [GMAIL_READONLY_SCOPE]
            row.config = merged
            row.last_sync_at = now
            row.connected_at = row.connected_at or now

        self.db.flush()
        self.db.add(
            SyncEvent(
                integration_id=row.id,
                event="Gmail sync completed" if reason != "webhook" else "Gmail webhook sync",
                status="success",
                detail=f"reason={reason}",
                occurred_at=now,
            )
        )
        self.db.commit()


def _header_map(message: dict[str, Any]) -> dict[str, str]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    result: dict[str, str] = {}
    for header in headers:
        name = (header.get("name") or "").strip().lower()
        if name:
            result[name] = str(header.get("value") or "")
    return result


def _parse_sender(from_header: str) -> dict[str, str]:
    match = re.match(r"^(.*?)\s*<([^>]+)>$", from_header.strip())
    if match:
        name = match.group(1).strip().strip('"') or match.group(2)
        email = match.group(2).strip()
    else:
        email = from_header.strip()
        name = email.split("@")[0] if email else "Unknown"
    initials = "".join(part[0] for part in name.replace(".", " ").split()[:2]).upper() or "?"
    return {
        "name": name[:100],
        "email": email[:255],
        "company": "",
        "avatar": initials[:10],
    }


def _parse_received(message: dict[str, Any], date_header: str | None) -> datetime | None:
    internal = message.get("internalDate")
    if internal is not None:
        try:
            return datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    if date_header:
        try:
            parsed = parsedate_to_datetime(date_header)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError, IndexError):
            return None
    return None


def _resolve_labels(label_ids: list[str], label_map: dict[str, str]) -> list[str]:
    names = []
    for label_id in label_ids:
        name = label_map.get(label_id, label_id)
        # Skip noisy system ids that duplicate unread/inbox state.
        if name in {"UNREAD", "INBOX"}:
            continue
        names.append(name)
    return names


def _category_from_labels(labels: list[str], label_ids: list[str]) -> str:
    upper = {label.upper() for label in labels} | {lid.upper() for lid in label_ids}
    if "IMPORTANT" in upper or "STARRED" in upper:
        return "high-priority"
    if "CATEGORY_UPDATES" in upper or "CATEGORY_PROMOTIONS" in upper:
        return "informational"
    if "CATEGORY_FORUMS" in upper or "CATEGORY_SOCIAL" in upper:
        return "informational"
    return "informational"


def _estimate_reading_time(text: str) -> str:
    words = len(text.split()) if text else 0
    minutes = max(1, (words + 199) // 200)
    return f"{minutes} min"
