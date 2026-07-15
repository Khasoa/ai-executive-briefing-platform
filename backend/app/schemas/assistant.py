from typing import Literal

from pydantic import BaseModel


class MessageSchema(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    id: str
    role: Literal["assistant"] = "assistant"
    content: str


class AssistantResponse(BaseModel):
    suggestions: list[str]
    history: list[MessageSchema]
