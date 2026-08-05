"""BriefAction — a single checklist item on a MorningBrief.

The only piece of brief state the executive edits directly (see
docs/decisions.md ADR-002 — Briefly recommends, it never acts on its own;
checking off a checklist item is the executive's own action, not the AI's).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BriefAction(Base):
    """A checklist item on a brief. The only state the executive edits directly."""

    __tablename__ = "brief_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("morning_briefs.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    due: Mapped[str] = mapped_column(String(100), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    brief: Mapped["MorningBrief"] = relationship(back_populates="actions")
