from typing import Literal

from pydantic import BaseModel


class EmailSchema(BaseModel):
    id: str
    from_: str
    subject: str
    summary: str
    time: str
    unread: bool
    actionRequired: bool | None = None

    model_config = {"populate_by_name": True}

    # Frontend expects "from" field; alias handles Python reserved keyword
    @classmethod
    def from_mock(cls, data: dict) -> "EmailSchema":
        return cls(
            id=data["id"],
            from_=data["from"],
            subject=data["subject"],
            summary=data["summary"],
            time=data["time"],
            unread=data["unread"],
            actionRequired=data.get("actionRequired"),
        )


class InboxCategorySchema(BaseModel):
    id: Literal["urgent", "clients", "investors", "finance", "internal", "newsletters"]
    label: str
    count: int
    emails: list[dict]


class InboxResponse(BaseModel):
    categories: list[InboxCategorySchema]
