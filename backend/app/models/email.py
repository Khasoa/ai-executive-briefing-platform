"""Email — a thread synced from Gmail, with generated summary and priority."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_user_category", "user_id", "category"),
        # Partial unique index created in migration 007:
        # uq_emails_user_external ON (user_id, external_id) WHERE external_id IS NOT NULL
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    sender: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    suggested_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reading_time: Mapped[str] = mapped_column(String(20), nullable=False, default="1 min")
    thread_count: Mapped[int] = mapped_column(Integer, default=1)
    unread: Mapped[bool] = mapped_column(Boolean, default=True)
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="emails")
