from sqlalchemy.orm import Session

from app.models import User
from app.schemas.workspace import WorkspaceResponse
from app.services.crm_service import CRMService
from app.services.demo_user import public_user_dict
from app.services.inbox_service import InboxService
from app.services.meeting_service import MeetingService
from app.services.morning_brief_service import MorningBriefService


class WorkspaceService:
    """Lightweight payload for the application shell — identity and nav counts.

    Badge counts go through `InboxService`, `MeetingService` and
    `CRMService` rather than reading `demo_data` directly, so the shell
    always reflects whichever source (database or mock) those services are
    actually serving. Brief freshness goes through
    `MorningBriefService.get_brief_meta()` for the same reason — the shell
    must not keep a separate opinion about when today's brief was generated.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_workspace(self) -> WorkspaceResponse:
        emails = InboxService(self.db, self.user).list_emails()
        meetings = MeetingService(self.db, self.user).list_meetings()
        opportunities = CRMService(self.db, self.user).list_opportunities()

        return WorkspaceResponse(
            user=public_user_dict(self.user),
            brief=MorningBriefService(self.db, self.user).get_brief_meta(),
            badges={
                "inbox": sum(1 for email in emails if email["unread"]),
                "meetings": len(meetings),
                "crm": sum(1 for o in opportunities if o["riskLevel"] in ("critical", "high")),
            },
        )
