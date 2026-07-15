from typing import Literal

from pydantic import BaseModel


class BriefMeetingSchema(BaseModel):
    time: str
    title: str
    note: str


class BriefPipelineSchema(BaseModel):
    company: str
    stage: str
    value: str
    note: str


class BriefDeadlineSchema(BaseModel):
    item: str
    due: str
    status: Literal["urgent", "high", "medium"]


class BriefRiskSchema(BaseModel):
    title: str
    description: str
    severity: Literal["high", "medium"]


class BriefSectionsSchema(BaseModel):
    priorities: list[str]
    meetings: list[BriefMeetingSchema]
    pipeline: list[BriefPipelineSchema]
    deadlines: list[BriefDeadlineSchema]
    risks: list[BriefRiskSchema]
    suggestedActions: list[str]


class DailyBriefResponse(BaseModel):
    date: str
    greeting: str
    sections: BriefSectionsSchema
