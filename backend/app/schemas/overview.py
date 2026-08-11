from typing import Literal

from pydantic import BaseModel

from app.schemas.common import (
    BriefMetaSchema,
    ClientAttentionSchema,
    PrioritySchema,
    RiskSchema,
    Source,
    Urgency,
)
from app.schemas.user import UserSchema


class MeetingToPrepareSchema(BaseModel):
    id: str
    title: str
    time: str
    reason: str


class RecommendedActionSchema(BaseModel):
    id: str
    label: str
    rationale: str


class ExecutiveSummarySchema(BaseModel):
    summary: str
    priorities: list[PrioritySchema]
    risks: list[RiskSchema]
    meetingsToPrepare: list[MeetingToPrepareSchema]
    clientsNeedingAttention: list[ClientAttentionSchema]
    recommendedActions: list[RecommendedActionSchema]


class KpiSchema(BaseModel):
    id: str
    label: str
    value: str
    sublabel: str
    change: str
    trend: Literal["up", "down", "neutral"]
    icon: Literal["inbox", "meetings", "deals", "tasks"]
    tone: Literal["primary", "accent", "slate"]


class ActivitySchema(BaseModel):
    id: str
    type: Literal["email", "deal", "document", "meeting", "task"]
    title: str
    detail: str
    time: str
    source: Source


class FocusRecommendationSchema(BaseModel):
    id: str
    title: str
    description: str
    rationale: str
    action: str
    actionTarget: str
    impact: str
    priority: Urgency
    sources: list[Source]


class OverviewResponse(BaseModel):
    user: UserSchema
    brief: BriefMetaSchema
    executiveSummary: ExecutiveSummarySchema
    kpis: list[KpiSchema]
    activity: list[ActivitySchema]
    focus: list[FocusRecommendationSchema]
