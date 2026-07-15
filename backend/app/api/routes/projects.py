from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.projects import ProjectsResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectsResponse)
def get_projects(db: Session = Depends(get_db)) -> ProjectsResponse:
    return ProjectService(db).get_projects()
