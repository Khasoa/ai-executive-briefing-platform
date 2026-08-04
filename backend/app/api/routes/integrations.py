from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.integrations import IntegrationsResponse
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=IntegrationsResponse)
def get_integrations(db: Session = Depends(get_db)) -> IntegrationsResponse:
    return IntegrationService(db).get_integrations()


@router.post("/{integration_id}/sync", response_model=IntegrationsResponse)
def sync_integration(integration_id: str, db: Session = Depends(get_db)) -> IntegrationsResponse:
    """Read from one system now. Returns the refreshed page including the audit entry."""
    return IntegrationService(db).trigger_sync(integration_id)
