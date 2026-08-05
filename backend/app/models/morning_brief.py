"""MorningBrief — the product's primary output: one generated briefing."""

import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MorningBrief(Base):
    """The product's primary output — one generated briefing."""

    __tablename__ = "morning_briefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    brief_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # priorities, risks, clients, focus blocks and delegation, keyed by section.
    sections: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    closing: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="briefs")
    actions: Mapped[list["BriefAction"]] = relationship(back_populates="brief")
