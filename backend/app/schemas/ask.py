from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import CitationSchema, Confidence


class SuggestedQuestionSchema(BaseModel):
    id: str
    question: str
    category: str
    icon: str


class RecentQuestionSchema(BaseModel):
    id: str
    question: str
    askedAt: str


class AskWorkspaceResponse(BaseModel):
    suggestions: list[SuggestedQuestionSchema]
    recent: list[RecentQuestionSchema]
    connectedSources: list[str]


class ReportItemSchema(BaseModel):
    title: str
    detail: str | None = None
    meta: str | None = None


class ReportSectionSchema(BaseModel):
    """A block of a report card. `items` and `body` are type-dependent."""

    id: str
    title: str
    type: Literal["ranked", "list", "text", "draft"]
    items: list[ReportItemSchema] = Field(default_factory=list)
    body: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question cannot be blank")
        return question


class AskReportResponse(BaseModel):
    id: str
    question: str
    answeredAt: str
    summary: str
    confidence: Confidence
    sections: list[ReportSectionSchema]
    citations: list[CitationSchema]
    followUps: list[str]
