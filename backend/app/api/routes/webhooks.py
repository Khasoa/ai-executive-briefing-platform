"""Inbound provider webhooks (Google Calendar + Gmail push notifications)."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.calendar_sync_service import CalendarSyncService
from app.services.gmail_sync_service import GmailSyncService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/google/calendar", status_code=status.HTTP_204_NO_CONTENT)
def google_calendar_webhook(
    db: Session = Depends(get_db),
    x_goog_channel_id: str | None = Header(default=None, alias="X-Goog-Channel-ID"),
    x_goog_resource_state: str | None = Header(default=None, alias="X-Goog-Resource-State"),
    x_goog_resource_id: str | None = Header(default=None, alias="X-Goog-Resource-ID"),
) -> Response:
    """Google Calendar push endpoint.

    Always returns 204 quickly. The initial ``sync`` handshake is acknowledged
    without pulling events; subsequent notifications trigger an incremental sync.
    """
    if not x_goog_channel_id:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    CalendarSyncService(db).handle_webhook(
        channel_id=x_goog_channel_id,
        resource_state=x_goog_resource_state,
        resource_id=x_goog_resource_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/google/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def google_gmail_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Gmail Pub/Sub push endpoint.

    Expects the standard Pub/Sub envelope. Decoded data should include
    ``emailAddress`` and optional ``historyId``. Always returns 204.
    """
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    message = (body or {}).get("message") or {}
    data_b64 = message.get("data")
    if not data_b64:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        decoded = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    email_address = (decoded.get("emailAddress") or "").strip().lower()
    history_id = decoded.get("historyId")
    if not email_address:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    GmailSyncService(db).handle_pubsub_notification(
        email_address=email_address,
        history_id=str(history_id) if history_id is not None else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
