import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Email, User
from app.schemas.inbox import EmailSchema, InboxResponse
from app.services import demo_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.demo_user import is_demo_user
from app.services.mapping_utils import stringify_id

logger = logging.getLogger("briefly.inbox")


class InboxService:
    """Turns raw threads into categorised, summarised executive mail.

    List reads never call OpenAI. Detail reads (`get_email`) fill empty AI
    fields once and persist them so later requests reuse the cache.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_inbox(self) -> InboxResponse:
        emails = self.list_emails()
        return InboxResponse(
            summary=demo_data.INBOX_SUMMARY,
            categories=self._categories(emails),
            emails=emails,
        )

    def get_email(self, email_id: str) -> EmailSchema:
        self._maybe_enrich_email(email_id)
        for email in self.list_emails():
            if email["id"] == email_id:
                return EmailSchema(**email)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email '{email_id}' not found",
        )

    def list_emails(self) -> list[dict]:
        """Read every email from PostgreSQL, falling back to `demo_data.EMAILS`."""
        fallback = demo_data.EMAILS if is_demo_user(self.user) else []
        return load_rows_with_fallback(
            query=lambda: (
                self.db.query(Email)
                .filter(Email.user_id == self.user.id)
                .order_by(Email.received_at.desc())
                .all()
            ),
            to_dict=self._to_dict,
            fallback=fallback,
            logger=logger,
            label="emails",
            db=self.db,
        )

    def _maybe_enrich_email(self, email_id: str) -> None:
        """Populate empty AI fields; never overwrite manual edits."""
        try:
            email_uuid = uuid.UUID(email_id)
        except ValueError:
            return

        try:
            row = (
                self.db.query(Email)
                .filter(Email.id == email_uuid, Email.user_id == self.user.id)
                .first()
            )
        except SQLAlchemyError:
            logger.warning("Could not load email for AI summary", exc_info=True)
            return

        if row is None:
            return

        summary_empty = not (row.ai_summary or "").strip()
        response_empty = not (row.suggested_response or "").strip()
        if not summary_empty and not response_empty:
            return

        from app.services.ai_service import AIService

        result = AIService(self.db, self.user).generate_email_summary(
            {
                "subject": row.subject,
                "sender": row.sender,
                "category": row.category,
                "priority": row.priority,
                "labels": row.labels or [],
                "readingTime": row.reading_time,
                "threadCount": row.thread_count,
                "receivedAt": row.received_at.isoformat() if row.received_at else None,
                "existingSummary": row.ai_summary or "",
            }
        )
        if result is None:
            return

        if summary_empty and result.get("summary"):
            row.ai_summary = result["summary"]
        if result.get("importance"):
            # Only bump priority when still at the sync default.
            if row.priority == "medium":
                row.priority = result["importance"]
        if response_empty and result.get("followUpSuggestion"):
            row.suggested_response = result["followUpSuggestion"]

        try:
            self.db.commit()
        except SQLAlchemyError:
            logger.warning("Could not persist email AI summary", exc_info=True)
            self.db.rollback()

    @staticmethod
    def _categories(emails: list[dict]) -> list[dict]:
        return [
            {
                **category,
                "count": sum(1 for email in emails if email["category"] == category["id"]),
            }
            for category in demo_data.INBOX_CATEGORIES
        ]

    @staticmethod
    def _to_dict(email: Email) -> dict:
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
