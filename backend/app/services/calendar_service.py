from sqlalchemy.orm import Session

from app.schemas.calendar import CalendarResponse
from app.services import mock_data


class CalendarService:
    """Provides calendar and meeting data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_calendar(self) -> CalendarResponse:
        # Future: integrate with Google Calendar via integrations/google_calendar.py
        return CalendarResponse(
            date="Wednesday, July 15, 2026",
            meetingCount=len(mock_data.MEETINGS),
            meetings=mock_data.MEETINGS,
        )
