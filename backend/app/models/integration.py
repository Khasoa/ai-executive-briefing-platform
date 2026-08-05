"""Integration — a connected provider (Gmail, Calendar, CRM, etc.) and its scopes."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="not-connected")
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # OAuth tokens and provider-specific configuration.
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="integrations")
    sync_events: Mapped[list["SyncEvent"]] = relationship(back_populates="integration")
