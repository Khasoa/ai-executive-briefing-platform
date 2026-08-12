"""Shared primitives reused across Briefly response schemas."""

from typing import Literal

from pydantic import BaseModel

Urgency = Literal["critical", "high", "medium", "low"]
Severity = Literal["critical", "high", "medium", "low"]
Confidence = Literal["high", "medium", "low"]

# Systems the AI can cite as the origin of a statement.
Source = Literal[
    "Gmail",
    "Google Calendar",
    "GoHighLevel",
    "Notion",
    "monday.com",
    "ClickUp",
    "OpenAI",
    "n8n",
]


class BriefMetaSchema(BaseModel):
    """Provenance for a generated brief — when, from what, how confident."""

    id: str
    date: str
    generatedAt: str
    generatedLabel: str
    confidence: Confidence
    sources: list[Source]
    headline: str


class PrioritySchema(BaseModel):
    id: str
    rank: int
    title: str
    detail: str
    urgency: Urgency
    owner: str
    source: Source


class RiskSchema(BaseModel):
    id: str
    title: str
    detail: str
    severity: Severity
    impact: str
    mitigation: str
    source: Source


class ClientAttentionSchema(BaseModel):
    id: str
    company: str
    stage: str
    value: str
    lastContact: str
    reason: str
    recommendedAction: str
    severity: Severity


class CitationSchema(BaseModel):
    """Tells the executive which system a piece of intelligence came from."""

    source: Source
    detail: str
    count: int
