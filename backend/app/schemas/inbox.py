from typing import Literal

from pydantic import BaseModel

EmailCategory = Literal[
    "needs-reply",
    "high-priority",
    "waiting",
    "delegated",
    "informational",
]


class SenderSchema(BaseModel):
    name: str
    email: str
    company: str
    avatar: str


class EmailSchema(BaseModel):
    id: str
    category: EmailCategory
    subject: str
    sender: SenderSchema
    timeLabel: str
    receivedAt: str
    aiSummary: str
    priority: Literal["critical", "high", "medium", "low"]
    suggestedResponse: str
    readingTime: str
    threadCount: int
    unread: bool
    labels: list[str]


class InboxCategorySchema(BaseModel):
    id: EmailCategory
    label: str
    description: str
    count: int


class InboxSummarySchema(BaseModel):
    headline: str
    totalUnread: int
    estimatedClearTime: str
    handledAutomatically: int


class InboxResponse(BaseModel):
    summary: InboxSummarySchema
    categories: list[InboxCategorySchema]
    emails: list[EmailSchema]
