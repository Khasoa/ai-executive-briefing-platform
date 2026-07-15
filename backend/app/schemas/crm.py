from pydantic import BaseModel


class OpportunitySchema(BaseModel):
    id: str
    company: str
    logo: str
    stage: str
    probability: int
    value: float
    owner: str
    lastActivity: str
    aiSummary: str
    tags: list[str]


class CRMResponse(BaseModel):
    opportunities: list[OpportunitySchema]
    pipelineTotal: float
