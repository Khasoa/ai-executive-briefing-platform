from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.assistant import AssistantResponse, ChatRequest, ChatResponse
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("", response_model=AssistantResponse)
def get_assistant(db: Session = Depends(get_db)) -> AssistantResponse:
    return AssistantService(db).get_assistant()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return AssistantService(db).chat(request.message)
