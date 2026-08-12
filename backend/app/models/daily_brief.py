"""DailyBrief — Phase 1 of the PostgreSQL migration.

Owned by a `User` so multi-tenant reads never leak another executive's brief.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DailyBrief(Base):
    """Phase 1 of the PostgreSQL migration: the first slice of the Morning Brief
    moved off `demo_data` and onto a real table.

    Only `summary`, `priorities` and `risks` are read today — see
    `OverviewService` for how those three fields are combined with curated data
    for everything else. `recommendations` and `executive_score` are captured
    here now so a later phase can start reading them without another schema
    change, but no service consumes them yet.

    `priorities` and `risks` are stored as JSONB shaped exactly like
    `PrioritySchema` / `RiskSchema` (see `app/schemas/common.py`), so a row
    read back from the database validates against the same response schema
    the API already returns from `demo_data` — no separate mapping needed.
    """

    __tablename__ = "daily_briefs"
    __table_args__ = (Index("ix_daily_briefs_user_generated", "user_id", "generated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
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

    user: Mapped["User"] = relationship(back_populates="daily_briefs")
