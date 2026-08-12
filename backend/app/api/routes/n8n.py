"""n8n orchestration webhooks — secret-authenticated, no business logic in n8n."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.schemas.email_follow_up import EmailFollowUpRequest, EmailFollowUpResponse
from app.services.email_follow_up_intelligence_service import EmailFollowUpIntelligenceService
from app.services.orchestration_service import ALL_PROVIDERS, OrchestrationService

router = APIRouter(prefix="/webhooks/n8n", tags=["n8n"])


class N8NRunRequest(BaseModel):
    userId: str | None = None
    userEmail: str | None = None
    providers: list[str] = Field(default_factory=lambda: list(ALL_PROVIDERS))
    regenerateMorningBrief: bool = False
    regenerateWeeklyDigest: bool = False


def _require_n8n_secret(
    x_briefly_n8n_secret: str | None = Header(default=None, alias="X-Briefly-N8N-Secret"),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = (settings.n8n_webhook_secret or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="n8n webhook secret is not configured",
        )
    provided = (x_briefly_n8n_secret or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid n8n webhook secret",
        )


@router.post("/run")
def n8n_run(
    payload: N8NRunRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_n8n_secret),
) -> dict[str, Any]:
    """Flexible orchestration entrypoint for n8n schedules.

    Syncs requested providers with per-step failure isolation, then optionally
    regenerates Morning Brief and/or Weekly Digest.
    """
    orch = OrchestrationService(db)
    user = orch.resolve_user(user_id=payload.userId, user_email=payload.userEmail)
    return orch.run(
        user,
        sync_providers=payload.providers,
        regenerate_morning_brief=payload.regenerateMorningBrief,
        regenerate_weekly_digest=payload.regenerateWeeklyDigest,
    )


@router.post("/daily")
def n8n_daily(
    payload: N8NRunRequest | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(_require_n8n_secret),
) -> dict[str, Any]:
    """Recommended daily workflow: sync all providers + regenerate Morning Brief."""
    body = payload or N8NRunRequest()
    orch = OrchestrationService(db)
    user = orch.resolve_user(user_id=body.userId, user_email=body.userEmail)
    return orch.run(
        user,
        sync_providers=body.providers or list(ALL_PROVIDERS),
        regenerate_morning_brief=True,
        regenerate_weekly_digest=False,
    )


@router.post("/weekly")
def n8n_weekly(
    payload: N8NRunRequest | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(_require_n8n_secret),
) -> dict[str, Any]:
    """Recommended weekly workflow: sync providers + regenerate Weekly Digest."""
    body = payload or N8NRunRequest()
    orch = OrchestrationService(db)
    user = orch.resolve_user(user_id=body.userId, user_email=body.userEmail)
    return orch.run(
        user,
        sync_providers=body.providers or list(ALL_PROVIDERS),
        regenerate_morning_brief=False,
        regenerate_weekly_digest=True,
    )


@router.post(
    "/email-follow-up",
    response_model=EmailFollowUpResponse,
    summary="Triage one email for executive action (n8n)",
    response_description="Structured follow-up intelligence — never sends email",
)
def n8n_email_follow_up(
    payload: EmailFollowUpRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_n8n_secret),
) -> EmailFollowUpResponse:
    """Analyze a single email and return whether the executive should act.

    Uses Briefly's existing AIService. Does not send replies, create tasks,
    or mutate inbox state. Authenticate with ``X-Briefly-N8N-Secret``.
    """
    orch = OrchestrationService(db)
    user = orch.resolve_user()
    return EmailFollowUpIntelligenceService(db, user).analyze(payload)
