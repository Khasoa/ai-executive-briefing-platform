from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.daily_brief import DailyBriefResponse
from app.schemas.overview import OverviewResponse
from app.services.overview_service import OverviewService

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)) -> OverviewResponse:
    return OverviewService(db).get_overview()


@router.get("/daily-brief", response_model=DailyBriefResponse)
def get_daily_brief(db: Session = Depends(get_db)) -> DailyBriefResponse:
    return OverviewService(db).get_daily_brief()
