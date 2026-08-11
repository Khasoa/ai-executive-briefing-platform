"""Map Google HTTP API failures to safe, actionable HTTPExceptions.

Never includes tokens, request Authorization headers, or raw response dumps
beyond the provider's public `error.message` / `reason` fields.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger("briefly.google_api")


def raise_for_google_response(
    response: httpx.Response,
    *,
    product: str,
    sync_token_expired_exc: type[Exception] | None = None,
) -> None:
    """Raise an HTTPException (or sync-token exception) for non-success responses.

    ``product`` is a human label such as ``Google Calendar`` or ``Gmail``.
    """
    code = response.status_code
    payload = _safe_error_payload(response)
    reason = _error_reason(payload)
    message = str((payload.get("error") or {}).get("message") or "").strip()

    logger.warning(
        "%s API HTTP %s reason=%s message=%s",
        product,
        code,
        reason or "unknown",
        (message[:180] + "…") if len(message) > 180 else message,
    )

    if code == 410 and sync_token_expired_exc is not None:
        raise sync_token_expired_exc()

    if code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{product} authorization needs to be refreshed. Reconnect Google.",
        )

    if reason == "accessNotConfigured" or (
        code == 403 and "has not been used" in message.lower()
    ):
        api_name = "Calendar" if "Calendar" in product else ("Gmail" if "Gmail" in product else product)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{product} API is not enabled for this Google Cloud project. "
                f"Enable the {api_name} API in Google Cloud Console, wait a few minutes, "
                "then Sync again."
            ),
        )

    if code == 403:
        if (
            "insufficient" in message.lower()
            or reason
            in (
                "insufficientPermissions",
                "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
                "forbidden",
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"{product} permission is missing or was revoked. "
                    "Reconnect Google to grant the required scopes."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{product} denied this request. Check Google account access and try again.",
        )

    if code == 404 and "Gmail" in product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail history cursor expired — a full sync is required.",
        )

    if code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{product} is temporarily unavailable. Try again shortly.",
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{product} sync failed (HTTP {code}). Try again or reconnect Google.",
    )


def _safe_error_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _error_reason(payload: dict[str, Any]) -> str:
    err = payload.get("error") or {}
    if isinstance(err, dict):
        errors = err.get("errors") or []
        if errors and isinstance(errors[0], dict):
            return str(errors[0].get("reason") or err.get("status") or "")
        return str(err.get("status") or "")
    return ""
