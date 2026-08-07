import logging

from sqlalchemy.orm import Session

from app.models import User
from app.schemas.overview import OverviewResponse
from app.services import demo_data
from app.services.daily_brief_service import DailyBriefService
from app.services.db_fallback import read_with_fallback
from app.services.demo_user import is_demo_user, public_user_dict
from app.services.meeting_service import MeetingService
from app.services.morning_brief_service import MorningBriefService

logger = logging.getLogger("briefly.overview")


class OverviewService:
    """Assembles the executive dashboard from every connected system.

    Phase 1 of the PostgreSQL migration lives here: `summary`, `priorities`
    and `risks` are read from the `daily_briefs` table when a row exists.
    Every other section — meetings, KPIs, activity, focus, recommended
    actions — still comes from `demo_data` for the demo tenant.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_overview(self) -> OverviewResponse:
        summary, priorities, risks = self._executive_summary_source()

        return OverviewResponse(
            user=public_user_dict(self.user),
            brief=MorningBriefService(self.db, self.user).get_brief_meta(),
            executiveSummary={
                "summary": summary,
                "priorities": priorities,
                "risks": risks,
                "meetingsToPrepare": self._meetings_to_prepare(),
                "clientsNeedingAttention": (
                    demo_data.CLIENTS_NEEDING_ATTENTION if is_demo_user(self.user) else []
                ),
                "recommendedActions": self._recommended_actions(),
            },
            kpis=demo_data.KPIS if is_demo_user(self.user) else [],
            activity=demo_data.ACTIVITY if is_demo_user(self.user) else [],
            focus=demo_data.TODAYS_FOCUS if is_demo_user(self.user) else [],
        )

    def _executive_summary_source(self) -> tuple[str, list, list]:
        brief = read_with_fallback(
            read=lambda: DailyBriefService(self.db, self.user).get_latest_brief(),
            fallback=None,
            logger=logger,
            label="daily_briefs",
            log_empty=False,
            db=self.db,
        )

        if brief is None:
            if is_demo_user(self.user):
                return demo_data.EXECUTIVE_SUMMARY_TEXT, demo_data.PRIORITIES, demo_data.RISKS
            return "", [], []

        return brief.summary, brief.priorities, brief.risks

    def _meetings_to_prepare(self) -> list[dict]:
        return [
            {
                "id": meeting["id"],
                "title": meeting["title"],
                "time": meeting["startTime"],
                "reason": meeting["prepReason"],
            }
            for meeting in MeetingService(self.db, self.user).list_meetings()
            if meeting["prepStatus"] == "needs-prep"
        ]

    def _recommended_actions(self) -> list[dict]:
        if not is_demo_user(self.user):
            return []
        return [
            {
                "id": f"act_{item['id']}",
                "label": item["title"],
                "rationale": item["rationale"],
            }
            for item in demo_data.TODAYS_FOCUS
        ]
