"""Email follow-up intelligence for n8n — analysis only, never sends mail."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.email_follow_up import EmailFollowUpRequest, EmailFollowUpResponse
from app.services.ai_service import AIService

logger = logging.getLogger("briefly.email_follow_up")

# Cap body size sent to the model; never log the body.
_MAX_BODY_CHARS = 12_000


class EmailFollowUpIntelligenceService:
    """Triage one email via existing AIService (no separate OpenAI client)."""

    def __init__(
        self,
        db: Session,
        user: User,
        *,
        ai: AIService | None = None,
    ) -> None:
        self.db = db
        self.user = user
        self.ai = ai or AIService(db, user)

    def analyze(self, payload: EmailFollowUpRequest) -> EmailFollowUpResponse:
        # Safe log — message id only; never log body.
        logger.info(
            "Email follow-up triage requested message_id=%s",
            payload.message_id[:120],
        )

        context = self._build_context(payload)
        result = self.ai.generate_email_follow_up(context)
        if result is None:
            logger.error(
                "Email follow-up triage failed for message_id=%s (malformed or unavailable AI)",
                payload.message_id[:120],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Email intelligence is temporarily unavailable",
            )

        return EmailFollowUpResponse(**result)

    @staticmethod
    def _build_context(payload: EmailFollowUpRequest) -> dict[str, Any]:
        body = payload.body or ""
        if len(body) > _MAX_BODY_CHARS:
            body = body[:_MAX_BODY_CHARS] + "\n…[truncated]"

        received: str | None
        if payload.received_at is None:
            received = None
        elif isinstance(payload.received_at, datetime):
            received = payload.received_at.isoformat()
        else:
            received = str(payload.received_at).strip() or None

        return {
            "message_id": payload.message_id,
            "thread_id": payload.thread_id,
            "sender": payload.sender,
            "subject": payload.subject,
            "received_at": received,
            "body": body,
        }
