"""Schemas for n8n email follow-up intelligence webhook."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmailFollowUpRequest(BaseModel):
    """One inbound email for executive triage (n8n → Briefly)."""

    message_id: str = Field(..., min_length=1, max_length=512)
    thread_id: str | None = None
    sender: str = Field(..., min_length=1, max_length=1000)
    subject: str = Field(..., min_length=1, max_length=2000)
    received_at: datetime | str | None = None
    body: str = Field(default="", max_length=100_000)


class EmailFollowUpResponse(BaseModel):
    """Structured triage result — analysis only; never sends mail."""

    requires_action: bool
    priority: Literal["low", "medium", "high"]
    category: str
    action: str | None = None
    deadline: str | None = None
    reason: str
    suggested_response: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
