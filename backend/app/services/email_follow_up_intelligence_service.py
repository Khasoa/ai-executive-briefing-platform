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

_CATEGORY_ACTION_HINTS = {
    "approval_request": "Review and approve or flag concerns",
    "meeting_request": "Confirm or decline the meeting request",
    "information_request": "Provide the requested information",
    "decision_needed": "Make the requested decision",
    "client_stakeholder": "Respond to the stakeholder request",
    "operational": "Address the operational issue raised",
}


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

        result = self._ensure_action_when_required(result, message_id=payload.message_id)
        return EmailFollowUpResponse(**result)

    @staticmethod
    def _ensure_action_when_required(
        result: dict[str, Any],
        *,
        message_id: str,
    ) -> dict[str, Any]:
        """Backstop: never ship requires_action=true with an empty action."""
        if not result.get("requires_action"):
            return result
        action = (result.get("action") or "").strip()
        if action:
            result["action"] = action
            return result

        fallback = EmailFollowUpIntelligenceService._derive_action_fallback(result)
        logger.warning(
            "Email follow-up empty action with requires_action=true; "
            "using derived fallback message_id=%s category=%s",
            message_id[:120],
            (result.get("category") or "")[:64],
        )
        result["action"] = fallback
        return result

    @staticmethod
    def _derive_action_fallback(result: dict[str, Any]) -> str:
        """Minimal instruction from category / reason / deadline — no invented facts."""
        category = (result.get("category") or "other").strip() or "other"
        hint = _CATEGORY_ACTION_HINTS.get(
            category,
            "Review this email and complete the requested action",
        )
        deadline = (result.get("deadline") or "").strip()
        reason = (result.get("reason") or "").strip()

        parts = [hint]
        if deadline:
            parts.append(f"by {deadline}")
        instruction = " ".join(parts).strip()
        if reason and len(reason) <= 160:
            # Keep reason as context only when short — do not invent new claims.
            return f"{instruction}. Context: {reason}"
        return instruction

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
