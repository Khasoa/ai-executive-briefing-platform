"""WorkItem — provider-neutral task/project row from monday.com or ClickUp."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "external_id", name="uq_work_items_user_provider_external"),
        Index("ix_work_items_user_provider", "user_id", "provider"),
        Index("ix_work_items_user_due", "user_id", "due_at"),
        Index("ix_work_items_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # monday | clickup
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    # e.g. monday:123456 or clickup:abc
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    container_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(40), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    labels: Mapped[list] = mapped_column(JSONB, default=list)
    # Provider-specific extras (board/list ids, raw status type, etc.)
    item_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    # AI enrichment — never overwritten by sync.
    intelligence: Mapped[dict] = mapped_column(JSONB, default=dict)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="work_items")
