from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.ask import AskReportResponse, AskRequest, AskWorkspaceResponse
from app.services.ask_service import AskService

router = APIRouter(prefix="/ask", tags=["ask"])


@router.get("", response_model=AskWorkspaceResponse)
def get_ask_workspace(db: Session = Depends(get_db)) -> AskWorkspaceResponse:
    return AskService(db).get_workspace()


@router.post("", response_model=AskReportResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskReportResponse:
    return AskService(db).answer(payload.question)
