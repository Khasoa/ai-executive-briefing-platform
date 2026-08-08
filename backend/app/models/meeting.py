"""Meeting — a calendar event plus the preparation Briefly generates for it."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (Index("ix_meetings_user_starts_at", "user_id", "starts_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    prep_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready")
    prep_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attendees: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    agenda: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Generated preparation: notes, talking points, questions and risks.
    intelligence: Mapped[dict] = mapped_column(JSONB, default=dict)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    user: Mapped["User"] = relationship(back_populates="meetings")
