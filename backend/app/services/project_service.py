from sqlalchemy.orm import Session

from app.schemas.projects import ProjectsResponse
from app.services import mock_data


class ProjectService:
    """Provides project and initiative tracking data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_projects(self) -> ProjectsResponse:
        # Future: integrate with ClickUp via integrations/clickup.py
        return ProjectsResponse(projects=mock_data.PROJECTS)
