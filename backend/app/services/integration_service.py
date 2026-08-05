import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Integration
from app.schemas.integrations import IntegrationsResponse
from app.services import mock_data

logger = logging.getLogger("briefly.integrations")


class IntegrationService:
    """Connection state and sync history for every upstream system.

    Phase 5 of the PostgreSQL migration: the `integrations` list is read
    from the `integrations` table when rows exist there, falling back to
    `mock_data.INTEGRATIONS` otherwise — including when the database itself
    is unreachable. Same fallback pattern as `MeetingService`,
    `InboxService` and `CRMService`; see `_load_integrations()` for the
    mechanics. `syncHistory` is out of scope for this phase (it is not
    "connection status") and stays sourced from `mock_data.SYNC_HISTORY`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_integrations(self) -> IntegrationsResponse:
        integrations = self._load_integrations()
        return IntegrationsResponse(
            connectedCount=sum(1 for i in integrations if i["status"] == "connected"),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=mock_data.SYNC_HISTORY,
        )

    def trigger_sync(self, integration_id: str) -> IntegrationsResponse:
        """Start a manual read and record it in the audit trail.

        Note on persistence: `integrations` is loaded once and reused for
        both the lookup and the response, so mutating the matched entry
        always shows up correctly in what this call returns. When the entry
        came from `mock_data` (a shared in-memory object), that mutation
        also persists for the lifetime of the process, exactly as before
        this migration. When it came from PostgreSQL, `_load_integrations()`
        builds a fresh dict per call, so the mutation only shapes *this*
        response rather than writing `status` back to the row — writing
        sync state to PostgreSQL is a separate concern from the connection
        status this phase persists, and is not part of this migration.
        """
        integrations = self._load_integrations()
        integration = next((i for i in integrations if i["id"] == integration_id), None)

        if integration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration '{integration_id}' not found",
            )

        if integration["status"] == "not-connected":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{integration['name']} is not connected yet",
            )

        integration["status"] = "syncing"
        integration["lastSyncLabel"] = "syncing now"

        mock_data.SYNC_HISTORY.insert(
            0,
            {
                "id": f"sync_{uuid4().hex[:8]}",
                "integrationId": integration["id"],
                "integration": integration["name"],
                "event": "Manual sync started",
                "status": "running",
                "time": datetime.now().strftime("%H:%M"),
                "detail": f"Requested from Integrations · {', '.join(integration['scopes'])}",
            },
        )

        return IntegrationsResponse(
            connectedCount=sum(1 for i in integrations if i["status"] == "connected"),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=mock_data.SYNC_HISTORY,
        )

    def _load_integrations(self) -> list[dict]:
        """Read every integration from PostgreSQL, falling back to `mock_data.INTEGRATIONS`.

        Fallback strategy: the same two situations as `MeetingService`,
        `InboxService` and `CRMService` land here — the table is reachable
        but empty (nothing seeded yet), or the database itself is
        unreachable (not migrated, connection dropped, credentials wrong).
        Both serve the curated integrations instead of an empty or broken
        response, so a database problem degrades this page rather than
        breaking it.
        """
        try:
            rows = self.db.query(Integration).order_by(Integration.provider.asc()).all()
        except SQLAlchemyError:
            logger.warning(
                "Could not read integrations — falling back to mock_data", exc_info=True
            )
            return mock_data.INTEGRATIONS

        if not rows:
            logger.info("No integrations in the database yet — serving mock_data")
            return mock_data.INTEGRATIONS

        return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(integration: Integration) -> dict:
        """Map an `Integration` row onto the exact dict shape `IntegrationSchema` expects.

        `status`, `account`, `scopes` and the sync timestamps map onto
        columns one-to-one. `name`, `category`, `description`, `metrics` and
        `poweredBy` are display metadata rather than connection state, and
        have no dedicated columns — like `Meeting.intelligence` and
        `Opportunity.last_interaction`, they ride inside the existing
        `config` JSONB blob (which already exists for provider-specific
        configuration) rather than requiring a schema change. `id` is the
        `provider` slug (e.g. "google-calendar"), not the row's UUID
        primary key, so it matches the stable ids the frontend already keys
        off (icons, sync buttons) and does not change the API contract.
        """
        config = integration.config or {}
        return {
            "id": integration.provider,
            "name": config.get("name", integration.provider),
            "category": config.get("category", ""),
            "description": config.get("description", ""),
            "status": integration.status,
            "account": integration.account,
            "lastSync": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "lastSyncLabel": IntegrationService._format_sync_label(
                integration.status, integration.last_sync_at
            ),
            "scopes": integration.scopes,
            "metrics": config.get("metrics", []),
            "poweredBy": config.get("poweredBy", ""),
        }

    @staticmethod
    def _format_sync_label(integration_status: str, last_sync_at: datetime | None) -> str:
        if integration_status == "syncing":
            return "syncing now"
        if last_sync_at is None:
            return "Never"

        now = datetime.now(timezone.utc)
        minutes = int((now - last_sync_at.astimezone(timezone.utc)).total_seconds() // 60)

        if minutes < 1:
            return "just now"
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        return f"{days} day{'s' if days != 1 else ''} ago"
