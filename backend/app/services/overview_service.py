import logging

from sqlalchemy.orm import Session

from app.schemas.overview import OverviewResponse
from app.services import mock_data
from app.services.daily_brief_service import DailyBriefService
from app.services.db_fallback import read_with_fallback
from app.services.meeting_service import MeetingService
from app.services.morning_brief_service import MorningBriefService

logger = logging.getLogger("briefly.overview")


class OverviewService:
    """Assembles the executive dashboard from every connected system.

    Phase 1 of the PostgreSQL migration lives here: `summary`, `priorities`
    and `risks` are read from the `daily_briefs` table when a row exists.
    Every other section — meetings, KPIs, activity, focus, recommended
    actions — still comes from `mock_data`.

    This is deliberately partial. Moving one section of the brief at a time
    keeps the app fully functional at every step, lets the new table prove
    itself under real traffic before the next section moves, and means a
    schema mistake in `daily_briefs` can only ever affect three fields rather
    than the whole dashboard.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_overview(self) -> OverviewResponse:
        summary, priorities, risks = self._executive_summary_source()

        return OverviewResponse(
            user=mock_data.USER,
            brief=MorningBriefService(self.db).get_brief_meta(),
            executiveSummary={
                "summary": summary,
                "priorities": priorities,
                "risks": risks,
                "meetingsToPrepare": self._meetings_to_prepare(),
                "clientsNeedingAttention": mock_data.CLIENTS_NEEDING_ATTENTION,
                "recommendedActions": self._recommended_actions(),
            },
            kpis=mock_data.KPIS,
            activity=mock_data.ACTIVITY,
            focus=mock_data.TODAYS_FOCUS,
        )

    def _executive_summary_source(self) -> tuple[str, list, list]:
        """Read `summary`/`priorities`/`risks` from PostgreSQL, falling back to `mock_data`.

        How SQLAlchemy retrieves it: `DailyBriefService.get_latest_brief()`
        runs `SELECT * FROM daily_briefs ORDER BY generated_at DESC LIMIT 1`
        through the ORM and maps the single row onto `DailyBriefSchema`.
        Because `priorities` and `risks` are stored as JSONB shaped like
        `PrioritySchema` / `RiskSchema`, the values that come back are already
        the exact shape `OverviewResponse` expects — no extra transformation
        happens in this method.

        Why the fallback exists: two distinct situations land here — no brief
        has been generated yet (an empty table), or the database itself is
        unreachable (not migrated, connection dropped, credentials wrong).
        Both are caught the same way, because from the dashboard's point of
        view they mean the same thing: there is nothing trustworthy in
        Postgres right now. Rather than let either case turn into a broken
        Overview page, we log a warning and use the curated `mock_data`
        values instead, so the rest of the dashboard is unaffected. Once
        `daily_briefs` is reliably populated in production, this fallback
        should rarely trigger — but it means a bad migration or a dropped
        connection degrades the brief instead of breaking the page.

        The try/except and the empty check are `read_with_fallback`, shared
        with the list-based loaders on `MeetingService`, `InboxService`,
        `CRMService` and `IntegrationService`. `log_empty=False` preserves
        this method's original behaviour exactly: no brief yet was never
        logged here, only an unreachable database was.
        """
        brief = read_with_fallback(
            read=lambda: DailyBriefService(self.db).get_latest_brief(),
            fallback=None,
            logger=logger,
            label="daily_briefs",
            log_empty=False,
            db=self.db,
        )

        if brief is None:
            return mock_data.EXECUTIVE_SUMMARY_TEXT, mock_data.PRIORITIES, mock_data.RISKS

        return brief.summary, brief.priorities, brief.risks

    def _meetings_to_prepare(self) -> list[dict]:
        # Goes through `MeetingService` rather than `mock_data.MEETINGS`
        # directly, so this section reflects real meetings the moment
        # `meetings` has rows — Phase 2's migration otherwise had no effect
        # on the Overview page at all.
        return [
            {
                "id": meeting["id"],
                "title": meeting["title"],
                "time": meeting["startTime"],
                "reason": meeting["prepReason"],
            }
            for meeting in MeetingService(self.db).list_meetings()
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
