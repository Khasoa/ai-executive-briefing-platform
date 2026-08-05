"""Small formatting helpers shared by every service's ORM-row-to-dict mapper.

Each migrated service (`MeetingService`, `InboxService`, `CRMService`,
`IntegrationService`, `MorningBriefService`) maps a SQLAlchemy row onto the
exact dict shape its Pydantic response schema expects. A handful of tiny
patterns showed up in more than one of them; everything else in each
`_to_dict` stays domain-specific on purpose — this is deliberately not a
general-purpose ORM mapper.
"""

from datetime import datetime, timezone
from typing import TypeVar

IdT = TypeVar("IdT")


def stringify_id(value: IdT) -> str:
    """A row's UUID primary key, as the string the API contract expects."""
    return str(value)


def jsonb_or_default(value: dict | None) -> dict:
    """A JSONB column that may be `None` (e.g. `intelligence`, `last_interaction`,
    `config`), defaulted to an empty dict so `.get(...)` is always safe."""
    return value or {}


def relative_time_label(past: datetime, *, now: datetime | None = None) -> str:
    """"just now" / "N minute(s) ago" / "N hour(s) ago" / "N day(s) ago".

    Shared by `IntegrationService` (`lastSyncLabel`) and `MorningBriefService`
    (`generatedLabel`) — both turn a timestamp column into the same style of
    freshness label, differing only in the special cases each wraps around
    this (`IntegrationService` has "syncing now" and "Never"; a brief's
    `generated_at` never is).
    """
    now = now or datetime.now(timezone.utc)
    minutes = int((now - past.astimezone(timezone.utc)).total_seconds() // 60)

    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"
