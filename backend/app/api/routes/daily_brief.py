from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.daily_brief import DailyBriefSchema
from app.services.daily_brief_service import DailyBriefService

router = APIRouter(prefix="/daily-brief", tags=["daily-brief"])


@router.get("/latest", response_model=DailyBriefSchema)
def get_latest_daily_brief(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DailyBriefSchema:
    """Direct read of the newest row in `daily_briefs` for the current user.

    Unlike `OverviewService`, this endpoint does not fall back to `demo_data`:
    its entire purpose is to reflect what is actually in PostgreSQL, so a
    missing brief (or an unreachable database) should surface as an error
    rather than be silently hidden.
    """
    brief = DailyBriefService(db, user).get_latest_brief()
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily brief has been generated yet",
        )
    return brief
