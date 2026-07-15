from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.research import ResearchResponse
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


@router.get("", response_model=ResearchResponse)
def get_research(db: Session = Depends(get_db)) -> ResearchResponse:
    return ResearchService(db).get_research()
