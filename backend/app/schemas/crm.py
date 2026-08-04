from pydantic import BaseModel

from app.schemas.common import Severity, Source


class LastInteractionSchema(BaseModel):
    type: str
    summary: str
    time: str


class OpportunitySchema(BaseModel):
    id: str
    company: str
    logo: str
    industry: str
    stage: str
    value: int
    probability: int
    owner: str
    closeDate: str
    riskLevel: Severity
    lastInteraction: LastInteractionSchema
    aiSummary: str
    recommendedAction: str
    signals: list[str]
    sources: list[Source]


class PipelineSummarySchema(BaseModel):
    pipelineValue: int
    weightedValue: int
    needingAttention: int
    closingThisMonth: int
    headline: str


class CRMResponse(BaseModel):
    summary: PipelineSummarySchema
    opportunities: list[OpportunitySchema]
