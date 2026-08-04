from sqlalchemy.orm import Session

from app.schemas.workspace import WorkspaceResponse
from app.services import mock_data


class WorkspaceService:
    """Lightweight payload for the application shell — identity and nav counts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_workspace(self) -> WorkspaceResponse:
        return WorkspaceResponse(
            user=mock_data.USER,
            brief=mock_data.BRIEF_META,
            badges={
                "inbox": sum(1 for email in mock_data.EMAILS if email["unread"]),
                "meetings": len(mock_data.MEETINGS),
                "crm": sum(
                    1 for o in mock_data.OPPORTUNITIES if o["riskLevel"] in ("critical", "high")
                ),
            },
        )
