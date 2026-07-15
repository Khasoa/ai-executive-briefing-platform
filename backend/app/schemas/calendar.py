from pydantic import BaseModel

from app.schemas.overview import MeetingSchema


class CalendarResponse(BaseModel):
    date: str
    meetingCount: int
    meetings: list[MeetingSchema]
