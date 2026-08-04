from sqlalchemy.orm import Session

from app.schemas.inbox import InboxResponse
from app.services import mock_data


class InboxService:
    """Turns raw threads into categorised, summarised executive mail."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_inbox(self) -> InboxResponse:
        return InboxResponse(
            summary=mock_data.INBOX_SUMMARY,
            categories=self._categories(),
            emails=mock_data.EMAILS,
        )

    @staticmethod
    def _categories() -> list[dict]:
        return [
            {
                **category,
                "count": sum(1 for email in mock_data.EMAILS if email["category"] == category["id"]),
            }
            for category in mock_data.INBOX_CATEGORIES
        ]
