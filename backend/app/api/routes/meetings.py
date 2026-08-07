from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.meetings import MeetingSchema, MeetingsResponse
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=MeetingsResponse)
def get_meetings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeetingsResponse:
    return MeetingService(db, user).get_meetings()


@router.get("/{meeting_id}", response_model=MeetingSchema)
def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeetingSchema:
    return MeetingService(db, user).get_meeting(meeting_id)
