from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Severity, Source

MeetingWindow = Literal["today", "tomorrow", "this_week", "this_month", "later", "past"]


class AttendeeSchema(BaseModel):
    name: str
    role: str = ""
    company: str = ""
    avatar: str = ""
    email: str | None = None


class MeetingCompanySchema(BaseModel):
    name: str = ""
    industry: str = ""
    size: str = ""
    relationship: str = ""
    background: str = ""
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
    # Additive timing / intelligence fields (older clients ignore unknown JSON).
    startsAt: str | None = None
    endsAt: str | None = None
    window: MeetingWindow | None = None
    relativeLabel: str | None = None
    dateLabel: str | None = None
    weekdayDateLabel: str | None = None
    timingLabel: str | None = None
    meetingLink: str | None = None
    organizer: AttendeeSchema | None = None
    isRecurring: bool = False
    recurringLabel: str | None = None
    prepRecommended: bool = False
    prepStatusLabel: str | None = None
    whyItMatters: str | None = None
    suggestedPrepActions: list[str] = Field(default_factory=list)
    prepHighlights: list[str] = Field(default_factory=list)
    contextNote: str | None = None
    relatedOpportunities: list[dict] = Field(default_factory=list)
    relatedWorkItems: list[dict] = Field(default_factory=list)


class MeetingWindowsSchema(BaseModel):
    today: list[MeetingSchema] = Field(default_factory=list)
    tomorrow: list[MeetingSchema] = Field(default_factory=list)
    thisWeek: list[MeetingSchema] = Field(default_factory=list)
    thisMonth: list[MeetingSchema] = Field(default_factory=list)
    later: list[MeetingSchema] = Field(default_factory=list)
    past: list[MeetingSchema] = Field(default_factory=list)


class MeetingsResponse(BaseModel):
    date: str
    meetingCount: int
    needsPreparation: int
    totalScheduledMinutes: int
    meetings: list[MeetingSchema]
    todayCount: int = 0
    needsPreparationToday: int = 0
    windows: MeetingWindowsSchema = Field(default_factory=MeetingWindowsSchema)
