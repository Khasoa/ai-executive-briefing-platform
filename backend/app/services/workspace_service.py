from sqlalchemy.orm import Session

from app.schemas.workspace import WorkspaceResponse
from app.services import mock_data
from app.services.crm_service import CRMService
from app.services.inbox_service import InboxService
from app.services.meeting_service import MeetingService
from app.services.morning_brief_service import MorningBriefService


class WorkspaceService:
    """Lightweight payload for the application shell — identity and nav counts.

    Badge counts go through `InboxService`, `MeetingService` and
    `CRMService` rather than reading `mock_data` directly, so the shell
    always reflects whichever source (database or mock) those services are
    actually serving. Brief freshness goes through
    `MorningBriefService.get_brief_meta()` for the same reason — the shell
    must not keep a separate opinion about when today's brief was generated.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_workspace(self) -> WorkspaceResponse:
        emails = InboxService(self.db).list_emails()
        meetings = MeetingService(self.db).list_meetings()
        opportunities = CRMService(self.db).list_opportunities()

        return WorkspaceResponse(
            user=mock_data.USER,
            brief=MorningBriefService(self.db).get_brief_meta(),
            badges={
                "inbox": sum(1 for email in emails if email["unread"]),
                "meetings": len(meetings),
                "crm": sum(1 for o in opportunities if o["riskLevel"] in ("critical", "high")),
            },
        )
