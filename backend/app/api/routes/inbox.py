from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.inbox import InboxResponse
from app.services.inbox_service import InboxService

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=InboxResponse)
def get_inbox(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InboxResponse:
    return InboxService(db, user).get_inbox()
