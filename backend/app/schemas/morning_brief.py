from typing import Literal

from pydantic import BaseModel

from app.schemas.common import (
    BriefMetaSchema,
    ClientAttentionSchema,
    PrioritySchema,
    RiskSchema,
)
from app.schemas.user import UserSchema


class BriefMeetingSchema(BaseModel):
    id: str
    time: str
    title: str
    attendees: list[str]
    prepStatus: Literal["ready", "needs-prep"]
    note: str


class BriefEmailSchema(BaseModel):
    id: str
    sender: str
    subject: str
    summary: str
    priority: Literal["critical", "high", "medium", "low"]
    waitingSince: str


class FocusBlockSchema(BaseModel):
    id: str
    start: str
    end: str
    label: str
    reason: str
    kind: Literal["deep-work", "decision", "quick-win", "review"]


class SuggestedFocusSchema(BaseModel):
    headline: str
    rationale: str
    blocks: list[FocusBlockSchema]


class DelegationSchema(BaseModel):
    id: str
    task: str
    assignee: str
    assigneeRole: str
    reason: str
    effort: str


class ChecklistItemSchema(BaseModel):
    id: str
    label: str
    category: Literal["Decision", "Reply", "Delegate", "Review"]
    due: str
    done: bool


class ChecklistUpdateRequest(BaseModel):
    done: bool


class ClosingAnswerSchema(BaseModel):
    question: str
    answer: str
    bullets: list[str]


class MorningBriefResponse(BaseModel):
    meta: BriefMetaSchema
    preparedFor: UserSchema
    executiveSummary: str
    topPriorities: list[PrioritySchema]
    criticalRisks: list[RiskSchema]
    meetings: list[BriefMeetingSchema]
    clientsNeedingAttention: list[ClientAttentionSchema]
    importantEmails: list[BriefEmailSchema]
    suggestedFocus: SuggestedFocusSchema
    recommendedDelegation: list[DelegationSchema]
    actionChecklist: list[ChecklistItemSchema]
    closing: ClosingAnswerSchema
