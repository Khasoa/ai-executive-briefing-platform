from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.weekly_digest import WeeklyDigestResponse
from app.services.weekly_digest_service import WeeklyDigestService

router = APIRouter(prefix="/weekly-digest", tags=["weekly-digest"])


@router.get("", response_model=WeeklyDigestResponse)
def get_weekly_digest(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyDigestResponse:
    """Latest Weekly Email Digest for the current 7-day window (cached)."""
    return WeeklyDigestService(db, user).get_digest()


@router.post("/regenerate", response_model=WeeklyDigestResponse)
def regenerate_weekly_digest(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeeklyDigestResponse:
    """Force a fresh digest from the last 7 days of email."""
    return WeeklyDigestService(db, user).regenerate()
