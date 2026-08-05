import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Email
from app.schemas.inbox import EmailSchema, InboxResponse
from app.services import mock_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.mapping_utils import stringify_id

logger = logging.getLogger("briefly.inbox")


class InboxService:
    """Turns raw threads into categorised, summarised executive mail.

    Phase 3 of the PostgreSQL migration: emails are read from the `emails`
    table when rows exist there, falling back to `mock_data.EMAILS`
    otherwise — including when the database itself is unreachable. This is
    the same fallback pattern used by `MeetingService`; see
    `list_emails()` for the mechanics. There is no separate "EmailService":
    `InboxService` already owns the `Email` domain end to end (categorising,
    counting and now loading it), so the database read lives here rather
    than in a new, duplicate service.

    `list_emails()` is public on purpose: it is the one place that knows how
    to load emails, so any other service that needs email data
    (`MorningBriefService`, `WorkspaceService`) calls it instead of reading
    `mock_data.EMAILS` directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_inbox(self) -> InboxResponse:
        emails = self.list_emails()
        return InboxResponse(
            summary=mock_data.INBOX_SUMMARY,
            categories=self._categories(emails),
            emails=emails,
        )

    def get_email(self, email_id: str) -> EmailSchema:
        # Reuses `list_emails()` rather than a dedicated lookup so a single
        # request never mixes a database-backed list with a mock-backed one,
        # matching the pattern established in `MeetingService.get_meeting()`.
        for email in self.list_emails():
            if email["id"] == email_id:
                return EmailSchema(**email)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email '{email_id}' not found",
        )

    def list_emails(self) -> list[dict]:
        """Read every email from PostgreSQL, falling back to `mock_data.EMAILS`.

        Fallback strategy: the same two situations as `MeetingService` land
        here — the table is reachable but empty (nothing seeded yet), or the
        database itself is unreachable (not migrated, connection dropped,
        credentials wrong). Both serve the curated emails instead of an
        empty or broken response, so a database problem degrades the inbox
        rather than breaking it. An empty result is logged at info level (a
        normal, expected state before seeding); a database error is logged
        as a warning (something is actually wrong). The actual try/except
        and empty check live in `load_rows_with_fallback`, shared with
        `MeetingService`, `CRMService` and `IntegrationService`.
        """
        return load_rows_with_fallback(
            query=lambda: self.db.query(Email).order_by(Email.received_at.desc()).all(),
            to_dict=self._to_dict,
            fallback=mock_data.EMAILS,
            logger=logger,
            label="emails",
            db=self.db,
        )

    @staticmethod
    def _categories(emails: list[dict]) -> list[dict]:
        # Counts follow whichever list `list_emails()` actually returned
        # (database or mock), so they always match the emails in the response.
        return [
            {
                **category,
                "count": sum(1 for email in emails if email["category"] == category["id"]),
            }
            for category in mock_data.INBOX_CATEGORIES
        ]

    @staticmethod
    def _to_dict(email: Email) -> dict:
        """Map an `Email` row onto the exact dict shape `EmailSchema` expects.

        Every field maps onto a column one-to-one except `timeLabel`, which
        the mock data hand-writes ("22:14 yesterday", "4 days ago") but the
        model does not store — it is derived from `received_at` instead, so
        the label always stays consistent with the timestamp.
        """
        return {
            "id": stringify_id(email.id),
            "category": email.category,
            "subject": email.subject,
            "sender": email.sender,
            "timeLabel": InboxService._format_time_label(email.received_at),
            "receivedAt": email.received_at.isoformat() if email.received_at else "",
            "aiSummary": email.ai_summary,
            "priority": email.priority,
            "suggestedResponse": email.suggested_response,
            "readingTime": email.reading_time,
            "threadCount": email.thread_count,
            "unread": email.unread,
            "labels": email.labels,
        }

    @staticmethod
    def _format_time_label(received_at: datetime | None) -> str:
        if received_at is None:
            return ""

        now = datetime.now(timezone.utc)
        received_utc = received_at.astimezone(timezone.utc)
        delta_days = (now.date() - received_utc.date()).days

        if delta_days <= 0:
            return received_utc.strftime("%H:%M")
        if delta_days == 1:
            return f"Yesterday, {received_utc.strftime('%H:%M')}"
        return f"{delta_days} days ago"
