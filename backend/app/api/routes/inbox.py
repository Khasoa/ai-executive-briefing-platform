from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.inbox import InboxResponse
from app.services.inbox_service import InboxService

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=InboxResponse)
def get_inbox(db: Session = Depends(get_db)) -> InboxResponse:
    return InboxService(db).get_inbox()
