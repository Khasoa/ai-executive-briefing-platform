from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.workspace import WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("", response_model=WorkspaceResponse)
def get_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    return WorkspaceService(db, user).get_workspace()
