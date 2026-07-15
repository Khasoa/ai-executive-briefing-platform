from sqlalchemy.orm import Session

from app.schemas.inbox import InboxResponse
from app.services import mock_data


class InboxService:
    """Provides AI-classified inbox data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_inbox(self) -> InboxResponse:
        # Future: integrate with Gmail via integrations/gmail.py
        return InboxResponse(categories=mock_data.INBOX_CATEGORIES)
