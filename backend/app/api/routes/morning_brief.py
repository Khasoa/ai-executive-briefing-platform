from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.morning_brief import (
    ChecklistItemSchema,
    ChecklistUpdateRequest,
    MorningBriefResponse,
)
from app.services.morning_brief_service import MorningBriefService

router = APIRouter(prefix="/morning-brief", tags=["morning-brief"])


@router.get("", response_model=MorningBriefResponse)
def get_morning_brief(db: Session = Depends(get_db)) -> MorningBriefResponse:
    return MorningBriefService(db).get_brief()


@router.post("/regenerate", response_model=MorningBriefResponse)
def regenerate_morning_brief(db: Session = Depends(get_db)) -> MorningBriefResponse:
    """Re-run the brief against the latest data from every connected system."""
    return MorningBriefService(db).regenerate()


@router.patch("/checklist/{item_id}", response_model=ChecklistItemSchema)
def update_checklist_item(
    item_id: str,
    payload: ChecklistUpdateRequest,
    db: Session = Depends(get_db),
) -> ChecklistItemSchema:
    return MorningBriefService(db).set_checklist_item(item_id, payload.done)
