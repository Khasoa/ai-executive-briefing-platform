from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.crm import CRMResponse
from app.services.crm_service import CRMService

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("", response_model=CRMResponse)
def get_crm(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CRMResponse:
    return CRMService(db, user).get_pipeline()
