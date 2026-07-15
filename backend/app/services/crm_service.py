from sqlalchemy.orm import Session

from app.schemas.crm import CRMResponse
from app.services import mock_data


class CRMService:
    """Provides CRM pipeline and deal data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_crm(self) -> CRMResponse:
        # Future: integrate with GoHighLevel via integrations/gohighlevel.py
        active = [o for o in mock_data.OPPORTUNITIES if o["stage"] != "Closed Won"]
        pipeline_total = sum(o["value"] for o in active)
        return CRMResponse(
            opportunities=mock_data.OPPORTUNITIES,
            pipelineTotal=pipeline_total,
        )
