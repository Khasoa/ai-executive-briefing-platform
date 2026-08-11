"""Timezone-aware windows for digest, brief, and overview surfaces."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import User


def user_zone(user: User | None) -> ZoneInfo:
    name = (getattr(user, "timezone", None) or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def now_in_user_tz(user: User | None) -> datetime:
    return datetime.now(timezone.utc).astimezone(user_zone(user))


def local_today(user: User | None) -> date:
    return now_in_user_tz(user).date()


def rolling_days_bounds(
    user: User | None, *, days: int = 7
) -> tuple[date, date, datetime, datetime]:
    """Inclusive local-date window covering the last ``days`` calendar days.

    Returns ``(start_date, end_date, start_dt_utc, end_dt_utc)``.
    """
    zone = user_zone(user)
    end_local = now_in_user_tz(user).date()
    start_local = end_local - timedelta(days=days - 1)
    start_dt = datetime.combine(start_local, datetime.min.time(), tzinfo=zone).astimezone(
        timezone.utc
    )
    end_dt = datetime.combine(end_local, datetime.max.time(), tzinfo=zone).astimezone(
        timezone.utc
    )
    return start_local, end_local, start_dt, end_dt


def upcoming_bounds(
    user: User | None, *, days: int = 14
) -> tuple[datetime, datetime]:
    """From now (UTC) through ``days`` ahead — for calendar outlook."""
    now = datetime.now(timezone.utc)
    return now, now + timedelta(days=days)


def overnight_bounds(user: User | None, *, hours: int = 18) -> tuple[datetime, datetime]:
    """Recent activity window for Overview Overnight."""
    end = datetime.now(timezone.utc)
    return end - timedelta(hours=hours), end


def local_day_bounds(user: User | None, day: date | None = None) -> tuple[datetime, datetime]:
    zone = user_zone(user)
    day = day or local_today(user)
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(day, datetime.max.time(), tzinfo=zone).astimezone(timezone.utc)
    return start, end
