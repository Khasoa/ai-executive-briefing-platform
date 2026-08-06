import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import Integration, SyncEvent
from app.schemas.integrations import IntegrationsResponse
from app.services import demo_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.mapping_utils import jsonb_or_default, relative_time_label, stringify_id

logger = logging.getLogger("briefly.integrations")


class IntegrationService:
    """Connection state and sync history for every upstream system.

    Phase 5 persisted `integrations`. The final production-readiness pass
    also persists `sync_events` (the Integrations page audit trail), with
    the same empty-table / `SQLAlchemyError` fallback to
    `demo_data.SYNC_HISTORY`. `list_integrations()` remains the single
    owner of connection state so other services (`AskService`) never read
    `demo_data.INTEGRATIONS` directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_integrations(self) -> IntegrationsResponse:
        integrations = self.list_integrations()
        return IntegrationsResponse(
            connectedCount=sum(1 for i in integrations if i["status"] == "connected"),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=self.list_sync_history(),
        )

    def trigger_sync(self, integration_id: str) -> IntegrationsResponse:
        """Start a manual read and record it in the audit trail.

        When the matched integration is a PostgreSQL row, this updates
        `status`/`last_sync_at` on that row and inserts a `SyncEvent`.
        When the matched entry came from `demo_data` (fallback path), the
        pre-migration behaviour is preserved: mutate the in-memory
        integration dict and prepend onto `demo_data.SYNC_HISTORY`.
        """
        integrations = self.list_integrations()
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

        detail = f"Requested from Integrations · {', '.join(integration['scopes'])}"
        persisted = self._persist_sync(integration_id, detail)

        integration["status"] = "syncing"
        integration["lastSyncLabel"] = "syncing now"

        if not persisted:
            demo_data.SYNC_HISTORY.insert(
                0,
                {
                    "id": f"sync_{uuid4().hex[:8]}",
                    "integrationId": integration["id"],
                    "integration": integration["name"],
                    "event": "Manual sync started",
                    "status": "running",
                    "time": datetime.now().strftime("%H:%M"),
                    "detail": detail,
                },
            )

        # Reload so the response reflects any persisted sync history /
        # status write. When persistence isn't available, rebuild from the
        # already-mutated in-memory list plus mock sync history.
        if persisted:
            return self.get_integrations()

        return IntegrationsResponse(
            connectedCount=sum(1 for i in integrations if i["status"] == "connected"),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=self.list_sync_history(),
        )

    def list_integrations(self) -> list[dict]:
        """Read every integration from PostgreSQL, falling back to `demo_data.INTEGRATIONS`."""
        return load_rows_with_fallback(
            query=lambda: self.db.query(Integration).order_by(Integration.provider.asc()).all(),
            to_dict=self._to_dict,
            fallback=demo_data.INTEGRATIONS,
            logger=logger,
            label="integrations",
            db=self.db,
        )

    def list_sync_history(self) -> list[dict]:
        """Read sync audit rows from PostgreSQL, falling back to `demo_data.SYNC_HISTORY`."""
        return load_rows_with_fallback(
            query=lambda: (
                self.db.query(SyncEvent)
                .options(joinedload(SyncEvent.integration))
                .order_by(SyncEvent.occurred_at.desc())
                .limit(50)
                .all()
            ),
            to_dict=self._sync_event_to_dict,
            fallback=demo_data.SYNC_HISTORY,
            logger=logger,
            label="sync_events",
            db=self.db,
        )

    def _persist_sync(self, provider: str, detail: str) -> bool:
        """Update the Integration row and insert a SyncEvent. Returns False on fallback."""
        try:
            row = (
                self.db.query(Integration)
                .filter(Integration.provider == provider)
                .first()
            )
            if row is None:
                return False

            now = datetime.now(timezone.utc)
            row.status = "syncing"
            row.last_sync_at = now
            self.db.add(
                SyncEvent(
                    integration_id=row.id,
                    event="Manual sync started",
                    status="running",
                    detail=detail,
                    occurred_at=now,
                )
            )
            self.db.commit()
            return True
        except SQLAlchemyError:
            logger.warning(
                "Could not persist sync for %s — falling back to demo_data",
                provider,
                exc_info=True,
            )
            self.db.rollback()
            return False

    @staticmethod
    def _to_dict(integration: Integration) -> dict:
        """Map an `Integration` row onto the exact dict shape `IntegrationSchema` expects.

        `id` is the `provider` slug (e.g. "google-calendar"), not the row's
        UUID primary key, so it matches the stable ids the frontend already
        keys off. Display metadata rides inside `config` JSONB.
        """
        config = jsonb_or_default(integration.config)
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
            "scopes": integration.scopes or [],
            "metrics": config.get("metrics", []),
            "poweredBy": config.get("poweredBy", ""),
        }

    @staticmethod
    def _sync_event_to_dict(event: SyncEvent) -> dict:
        integration = event.integration
        config = jsonb_or_default(integration.config if integration else None)
        provider = integration.provider if integration else ""
        name = config.get("name", provider)
        occurred = event.occurred_at
        return {
            "id": stringify_id(event.id),
            "integrationId": provider,
            "integration": name,
            "event": event.event,
            "status": event.status,
            "time": occurred.strftime("%H:%M") if occurred else "",
            "detail": event.detail,
        }

    @staticmethod
    def _format_sync_label(integration_status: str, last_sync_at: datetime | None) -> str:
        if integration_status == "syncing":
            return "syncing now"
        if last_sync_at is None:
            return "Never"
        return relative_time_label(last_sync_at)
