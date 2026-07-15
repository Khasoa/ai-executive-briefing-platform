from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.calendar import CalendarResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=CalendarResponse)
def get_calendar(db: Session = Depends(get_db)) -> CalendarResponse:
    return CalendarService(db).get_calendar()
