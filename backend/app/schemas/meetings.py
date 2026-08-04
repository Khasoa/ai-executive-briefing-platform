from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Severity, Source


class AttendeeSchema(BaseModel):
    name: str
    role: str
    company: str
    avatar: str


class MeetingCompanySchema(BaseModel):
    name: str
    industry: str
    size: str
    relationship: str
    background: str
    arr: str | None = None


class RelatedEmailSchema(BaseModel):
    id: str
    subject: str
    sender: str
    summary: str
    time: str


class MeetingRiskSchema(BaseModel):
    title: str
    detail: str
    severity: Severity


class MeetingSchema(BaseModel):
    id: str
    title: str
    startTime: str
    endTime: str
    duration: str
    type: Literal["internal", "client", "investor", "personal"]
    location: str
    prepStatus: Literal["ready", "needs-prep"]
    prepReason: str
    attendees: list[AttendeeSchema]
    agenda: list[str]
    company: MeetingCompanySchema
    relatedEmails: list[RelatedEmailSchema]
    preparationNotes: list[str]
    talkingPoints: list[str]
    recommendedQuestions: list[str]
    risks: list[MeetingRiskSchema]
    sources: list[Source]


class MeetingsResponse(BaseModel):
    date: str
    meetingCount: int
    needsPreparation: int
    totalScheduledMinutes: int
    meetings: list[MeetingSchema]
