"""API contract for the `daily_briefs` table — Phase 1 of the PostgreSQL migration.

`priorities` and `risks` reuse `PrioritySchema` / `RiskSchema` from
`app/schemas/common.py` on purpose: those are the exact shapes `OverviewService`
already returns from `mock_data`, so a database-backed brief and a curated one
are indistinguishable to the frontend.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import PrioritySchema, RiskSchema


class DailyBriefRecommendationSchema(BaseModel):
    """Not yet read by any service — captured now to avoid a schema change later."""

    id: str
    title: str
    rationale: str


class DailyBriefSchema(BaseModel):
    id: str
    generatedAt: datetime
    summary: str
    priorities: list[PrioritySchema]
    risks: list[RiskSchema]
    recommendations: list[DailyBriefRecommendationSchema]
    executiveScore: int
    createdAt: datetime
