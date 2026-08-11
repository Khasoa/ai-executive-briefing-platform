"""NotionItem — a page or database row synced from Notion for briefing context."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotionItem(Base):
    __tablename__ = "notion_items"
    __table_args__ = (
        Index("ix_notion_items_user_kind", "user_id", "kind"),
        Index("ix_notion_items_user_edited", "user_id", "last_edited_at"),
        # Partial unique index created in migration 009:
        # uq_notion_items_user_external ON (user_id, external_id) WHERE external_id IS NOT NULL
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    object_type: Mapped[str] = mapped_column(String(30), nullable=False, default="page")
    # task | project | note | decision | meeting_notes | database | other
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="note")
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_database_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Raw Notion properties useful for classification / Ask context.
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_preview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # AI-generated enrichment — never overwritten by sync.
    intelligence: Mapped[dict] = mapped_column(JSONB, default=dict)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    user: Mapped["User"] = relationship(back_populates="notion_items")
