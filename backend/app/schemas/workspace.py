from pydantic import BaseModel

from app.schemas.common import BriefMetaSchema
from app.schemas.user import UserSchema


class NavBadgesSchema(BaseModel):
    """Counts the shell renders next to navigation items."""

    inbox: int
    meetings: int
    crm: int


class WorkspaceResponse(BaseModel):
    user: UserSchema
    brief: BriefMetaSchema
    badges: NavBadgesSchema
