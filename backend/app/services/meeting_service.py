from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.meetings import MeetingSchema, MeetingsResponse
from app.services import mock_data


class MeetingService:
    """Meeting intelligence: context and preparation rather than a calendar grid."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_meetings(self) -> MeetingsResponse:
        meetings = mock_data.MEETINGS
        return MeetingsResponse(
            date=mock_data.BRIEF_DATE,
            meetingCount=len(meetings),
            needsPreparation=sum(1 for m in meetings if m["prepStatus"] == "needs-prep"),
            totalScheduledMinutes=sum(self._minutes(m) for m in meetings),
            meetings=meetings,
        )

    def get_meeting(self, meeting_id: str) -> MeetingSchema:
        for meeting in mock_data.MEETINGS:
            if meeting["id"] == meeting_id:
                return MeetingSchema(**meeting)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting '{meeting_id}' not found",
        )

    @staticmethod
    def _minutes(meeting: dict) -> int:
        start_hour, start_minute = (int(part) for part in meeting["startTime"].split(":"))
        end_hour, end_minute = (int(part) for part in meeting["endTime"].split(":"))
        return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
