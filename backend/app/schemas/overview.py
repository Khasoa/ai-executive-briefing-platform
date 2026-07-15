from typing import Literal

from pydantic import BaseModel

from app.schemas.user import UserSchema


class PrioritySchema(BaseModel):
    id: str
    text: str
    urgency: Literal["critical", "high", "medium"]


class ExecutiveSummarySchema(BaseModel):
    generatedAt: str
    summary: str
    priorities: list[PrioritySchema]


class KpiSchema(BaseModel):
    id: str
    label: str
    value: str
    sublabel: str
    change: str
    trend: Literal["up", "down", "neutral"]
    icon: Literal["inbox", "calendar", "pipeline", "projects"]
    color: str


class AIRecommendationSchema(BaseModel):
    id: str
    title: str
    description: str
    action: str
    priority: Literal["high", "medium"]


class MeetingSchema(BaseModel):
    id: str
    title: str
    time: str
    duration: str
    attendees: list[str]
    type: Literal["internal", "client", "investor"]
    location: str


class ActivitySchema(BaseModel):
    id: str
    type: Literal["email", "deal", "project", "meeting", "crm"]
    title: str
    time: str
    icon: Literal["mail", "trending", "file", "calendar", "user"]


class OverviewResponse(BaseModel):
    user: UserSchema
    executiveSummary: ExecutiveSummarySchema
    kpis: list[KpiSchema]
    aiRecommendations: list[AIRecommendationSchema]
    meetings: list[MeetingSchema]
    activities: list[ActivitySchema]
