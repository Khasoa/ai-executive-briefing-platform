"""DailyBrief — Phase 1 of the PostgreSQL migration.

The first slice of the Morning Brief moved off `mock_data` and onto a real
table. Has no relationships to other models (yet) — it stands alone.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyBrief(Base):
    """Phase 1 of the PostgreSQL migration: the first slice of the Morning Brief
    moved off `mock_data` and onto a real table.

    Only `summary`, `priorities` and `risks` are read today — see
    `OverviewService` for how those three fields are combined with curated data
    for everything else. `recommendations` and `executive_score` are captured
    here now so a later phase can start reading them without another schema
    change, but no service consumes them yet.

    `priorities` and `risks` are stored as JSONB shaped exactly like
    `PrioritySchema` / `RiskSchema` (see `app/schemas/common.py`), so a row
    read back from the database validates against the same response schema
    the API already returns from `mock_data` — no separate mapping needed.
    """

    __tablename__ = "daily_briefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priorities: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    recommendations: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    executive_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
