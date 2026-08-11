"""WeeklyDigest — cached weekly email memory + next-week planning note."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_digest_user_week"),
        Index("ix_weekly_digests_user_week", "user_id", "week_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    planning_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # openai | curated
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="curated")
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Section arrays keyed by name (important_conversations, etc.)
    sections: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="weekly_digests")
