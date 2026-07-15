import time

from sqlalchemy.orm import Session

from app.schemas.assistant import AssistantResponse, ChatResponse
from app.services import mock_data


class AssistantService:
    """Provides AI assistant chat functionality."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_assistant(self) -> AssistantResponse:
        return AssistantResponse(
            suggestions=mock_data.CHAT_SUGGESTIONS,
            history=mock_data.CHAT_HISTORY,
        )

    def chat(self, message: str) -> ChatResponse:
        # Future: integrate with OpenAI via integrations/openai.py
        content = mock_data.AI_RESPONSES.get(message, mock_data.DEFAULT_AI_RESPONSE)
        return ChatResponse(
            id=str(int(time.time() * 1000)),
            content=content,
        )
