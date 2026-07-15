from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.crm import CRMResponse
from app.services.crm_service import CRMService

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("", response_model=CRMResponse)
def get_crm(db: Session = Depends(get_db)) -> CRMResponse:
    return CRMService(db).get_crm()
