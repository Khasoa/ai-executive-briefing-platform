from sqlalchemy.orm import Session

from app.schemas.research import ResearchResponse
from app.services import mock_data


class ResearchService:
    """Provides AI-curated business intelligence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_research(self) -> ResearchResponse:
        return ResearchResponse(items=mock_data.RESEARCH_ITEMS)
