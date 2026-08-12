"""SQLAlchemy models for Briefly — one file per table.

Every model is imported here so the shared declarative registry (`Base`, from
`app.db.base`) is fully populated whenever anything does
`from app.models import ...`. That matters for two things:

1. Relationships declared with string forward references (e.g.
   `Mapped["MorningBrief"]` on `User`) are resolved lazily by SQLAlchemy
   against that shared registry — they work regardless of which file a class
   lives in, as long as every model has been imported by the time mappers
   are configured. Importing them all here guarantees that.
2. Alembic's `env.py` imports from this package to populate
   `Base.metadata` before comparing it against the database, so autogenerate
   needs every model represented here to see every table.
"""

from app.models.ask_report import AskReport
from app.models.brief_action import BriefAction
from app.models.daily_brief import DailyBrief
from app.models.email import Email
from app.models.integration import Integration
from app.models.meeting import Meeting
from app.models.morning_brief import MorningBrief
from app.models.notion_item import NotionItem
from app.models.oauth_state import OAuthLoginTicket, OAuthState
from app.models.opportunity import Opportunity
from app.models.refresh_token import RefreshToken
from app.models.sync_event import SyncEvent
from app.models.user import User
from app.models.weekly_digest import WeeklyDigest
from app.models.work_item import WorkItem

__all__ = [
    "AskReport",
    "BriefAction",
    "DailyBrief",
    "Email",
    "Integration",
    "Meeting",
    "MorningBrief",
    "NotionItem",
    "OAuthLoginTicket",
    "OAuthState",
    "Opportunity",
    "RefreshToken",
    "SyncEvent",
    "User",
    "WeeklyDigest",
    "WorkItem",
]
