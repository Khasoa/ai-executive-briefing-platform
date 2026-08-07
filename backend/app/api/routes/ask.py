from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.ask import AskReportResponse, AskRequest, AskWorkspaceResponse
from app.services.ask_service import AskService

router = APIRouter(prefix="/ask", tags=["ask"])


@router.get("", response_model=AskWorkspaceResponse)
def get_ask_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AskWorkspaceResponse:
    return AskService(db, user).get_workspace()


@router.post("", response_model=AskReportResponse)
def ask_question(
    payload: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AskReportResponse:
    return AskService(db, user).answer(payload.question)
