from typing import Literal

from pydantic import BaseModel


class ResearchItemSchema(BaseModel):
    id: str
    title: str
    source: str
    summary: str
    relevance: Literal["high", "medium"]
    date: str


class ResearchResponse(BaseModel):
    items: list[ResearchItemSchema]
