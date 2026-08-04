from sqlalchemy.orm import Session

from app.schemas.overview import OverviewResponse
from app.services import mock_data


class OverviewService:
    """Assembles the executive dashboard from every connected system."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_overview(self) -> OverviewResponse:
        return OverviewResponse(
            user=mock_data.USER,
            brief=mock_data.BRIEF_META,
            executiveSummary={
                "summary": mock_data.EXECUTIVE_SUMMARY_TEXT,
                "priorities": mock_data.PRIORITIES,
                "risks": mock_data.RISKS,
                "meetingsToPrepare": self._meetings_to_prepare(),
                "clientsNeedingAttention": mock_data.CLIENTS_NEEDING_ATTENTION,
                "recommendedActions": self._recommended_actions(),
            },
            kpis=mock_data.KPIS,
            activity=mock_data.ACTIVITY,
            focus=mock_data.TODAYS_FOCUS,
        )

    @staticmethod
    def _meetings_to_prepare() -> list[dict]:
        return [
            {
                "id": meeting["id"],
                "title": meeting["title"],
                "time": meeting["startTime"],
                "reason": meeting["prepReason"],
            }
            for meeting in mock_data.MEETINGS
            if meeting["prepStatus"] == "needs-prep"
        ]

    @staticmethod
    def _recommended_actions() -> list[dict]:
        return [
            {
                "id": f"act_{item['id']}",
                "label": item["title"],
                "rationale": item["rationale"],
            }
            for item in mock_data.TODAYS_FOCUS
        ]
