"""Timezone-aware meeting time windows shared across Overview / Brief / Digest / Meetings."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from app.models import User
from app.services.time_windows import local_today, now_in_user_tz, user_zone

MeetingWindow = Literal["today", "tomorrow", "this_week", "this_month", "later", "past"]

WINDOW_ORDER: tuple[MeetingWindow, ...] = (
    "today",
    "tomorrow",
    "this_week",
    "this_month",
    "later",
    "past",
)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def classify_meeting_at(
    starts_at: datetime | None,
    user: User | None,
    *,
    now: datetime | None = None,
) -> MeetingWindow:
    """Classify a meeting start into a product window using the user's timezone."""
    if starts_at is None:
        return "later"

    zone = user_zone(user)
    local_now = (now or datetime.now(timezone.utc)).astimezone(zone)
    start_local = ensure_aware(starts_at).astimezone(zone)
    today = local_now.date()
    meeting_day = start_local.date()

    if meeting_day < today:
        return "past"
    if meeting_day == today:
        return "today"
    if meeting_day == today + timedelta(days=1):
        return "tomorrow"

    # this_week: remaining days of the local calendar week (Mon–Sun), excluding today/tomorrow
    week_end = today + timedelta(days=(6 - today.weekday()))
    if meeting_day <= week_end:
        return "this_week"

    if meeting_day.year == today.year and meeting_day.month == today.month:
        return "this_month"

    return "later"


def relative_meeting_label(
    starts_at: datetime | None,
    user: User | None,
    *,
    now: datetime | None = None,
) -> str:
    """Human relative timing, e.g. 'in 2h 15m', 'Today', 'Tomorrow', 'In 3 days'."""
    if starts_at is None:
        return ""

    zone = user_zone(user)
    local_now = (now or datetime.now(timezone.utc)).astimezone(zone)
    start_local = ensure_aware(starts_at).astimezone(zone)
    meeting_day = start_local.date()
    today = local_now.date()

    if meeting_day == today:
        delta = start_local - local_now
        seconds = int(delta.total_seconds())
        if seconds < 0:
            mins = abs(seconds) // 60
            if mins < 60:
                return f"{mins}m ago" if mins else "just now"
            hours = mins // 60
            rem = mins % 60
            return f"{hours}h {rem}m ago" if rem else f"{hours}h ago"
        mins = seconds // 60
        if mins < 60:
            return f"in {mins}m" if mins else "starting now"
        hours = mins // 60
        rem = mins % 60
        return f"in {hours}h {rem}m" if rem else f"in {hours}h"

    if meeting_day == today + timedelta(days=1):
        return "Tomorrow"

    if meeting_day < today:
        days = (today - meeting_day).days
        return f"{days} day{'s' if days != 1 else ''} ago"

    days = (meeting_day - today).days
    return f"In {days} days"


def short_date_label(
    starts_at: datetime | None,
    user: User | None,
) -> str:
    """Local calendar date, e.g. 'Aug 11'."""
    if starts_at is None:
        return ""
    zone = user_zone(user)
    local = ensure_aware(starts_at).astimezone(zone)
    return f"{local.strftime('%b')} {local.day}"


def weekday_date_label(
    starts_at: datetime | None,
    user: User | None,
) -> str:
    """Local weekday + date, e.g. 'Friday, Aug 14'."""
    if starts_at is None:
        return ""
    zone = user_zone(user)
    local = ensure_aware(starts_at).astimezone(zone)
    return f"{local.strftime('%A')}, {local.strftime('%b')} {local.day}"


def timing_display_label(
    starts_at: datetime | None,
    user: User | None,
    *,
    now: datetime | None = None,
) -> str:
    """Combined relative + actual date: 'Today · Aug 11', 'In 18 days · Aug 29'."""
    if starts_at is None:
        return ""
    zone = user_zone(user)
    local_now = (now or datetime.now(timezone.utc)).astimezone(zone)
    start_local = ensure_aware(starts_at).astimezone(zone)
    meeting_day = start_local.date()
    today = local_now.date()
    date_part = short_date_label(starts_at, user)

    if meeting_day == today:
        return f"Today · {date_part}"
    if meeting_day == today + timedelta(days=1):
        return f"Tomorrow · {date_part}"
    if meeting_day < today:
        days = (today - meeting_day).days
        return f"{days} day{'s' if days != 1 else ''} ago · {date_part}"
    days = (meeting_day - today).days
    return f"In {days} days · {date_part}"


def prep_recommended_for_window(
    window: MeetingWindow,
    prep_status: str | None,
) -> bool:
    """Only today's meetings normally recommend preparation / Today's Focus."""
    if window != "today":
        return False
    return (prep_status or "needs-prep") == "needs-prep"


def dedupe_meetings_by_title_start(meetings: list) -> list:
    """Collapse presentation duplicates sharing title + start (distinct Google IDs)."""
    seen: set[tuple[str, str]] = set()
    out: list = []
    for meeting in meetings:
        if hasattr(meeting, "title"):
            title = (meeting.title or "").strip().lower()
            starts = meeting.starts_at
            key_start = starts.isoformat()[:16] if starts else ""
        else:
            title = (meeting.get("title") or "").strip().lower()
            key_start = (meeting.get("startsAt") or meeting.get("startTime") or "")[:16]
        key = (title, key_start)
        if key in seen:
            continue
        seen.add(key)
        out.append(meeting)
    return out


def format_local_date_label(user: User | None, day: date | None = None) -> str:
    day = day or local_today(user)
    return f"{day.strftime('%A, %B')} {day.day}, {day.year}"
