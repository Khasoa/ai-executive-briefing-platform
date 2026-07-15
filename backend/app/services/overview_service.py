from sqlalchemy.orm import Session

from app.schemas.daily_brief import DailyBriefResponse
from app.schemas.overview import OverviewResponse
from app.services import mock_data


class OverviewService:
    """Aggregates executive dashboard data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_overview(self) -> OverviewResponse:
        # Future: query User, Meeting, Email, CRMDeal from database
        return OverviewResponse(
            user=mock_data.USER,
            executiveSummary=mock_data.EXECUTIVE_SUMMARY,
            kpis=mock_data.KPIS,
            aiRecommendations=mock_data.AI_RECOMMENDATIONS,
            meetings=mock_data.MEETINGS,
            activities=mock_data.ACTIVITIES,
        )

    def get_daily_brief(self) -> DailyBriefResponse:
        return DailyBriefResponse(**mock_data.DAILY_BRIEF)
