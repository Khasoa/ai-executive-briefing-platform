from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.integrations import IntegrationsResponse
from app.services import mock_data


class IntegrationService:
    """Connection state and sync history for every upstream system."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_integrations(self) -> IntegrationsResponse:
        integrations = mock_data.INTEGRATIONS
        return IntegrationsResponse(
            connectedCount=sum(1 for i in integrations if i["status"] == "connected"),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=mock_data.SYNC_HISTORY,
        )

    def trigger_sync(self, integration_id: str) -> IntegrationsResponse:
        """Start a manual read and record it in the audit trail."""
        integration = self._find(integration_id)

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

        return self.get_integrations()

    def _find(self, integration_id: str) -> dict:
        for integration in mock_data.INTEGRATIONS:
            if integration["id"] == integration_id:
                return integration

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
