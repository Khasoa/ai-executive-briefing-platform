"""Shared fallback pattern for services that read from PostgreSQL.

Every migrated service (`MeetingService`, `InboxService`, `CRMService`,
`IntegrationService`, and `OverviewService`'s read of the latest
`DailyBrief`) treats two situations the same way: the table is reachable
but empty (nothing seeded yet), or the database itself is unreachable (not
migrated, connection dropped, credentials wrong). Both fall back to curated
`mock_data`, differing only in log level — info for "empty", warning for
"error" — because from the caller's point of view both mean "there is
nothing trustworthy in Postgres right now."

Before this module, every service re-implemented that try/except and
empty-check by hand. This extracts it once so the pattern (and its log
levels) can't drift between services.
"""

import logging
from typing import Callable, Sequence, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

RowT = TypeVar("RowT")
ValueT = TypeVar("ValueT")


def load_rows_with_fallback(
    *,
    query: Callable[[], Sequence[RowT]],
    to_dict: Callable[[RowT], dict],
    fallback: list[dict],
    logger: logging.Logger,
    label: str,
    db: Session | None = None,
) -> list[dict]:
    """Run `query()`, map every row with `to_dict`, falling back to `fallback`.

    - `query()` raises `SQLAlchemyError` → log a warning, return `fallback`.
    - `query()` returns no rows → log at info level, return `fallback`.
    - Otherwise → return `[to_dict(row) for row in rows]`.

    `db` is optional and only used to roll back the session on error. A
    failed statement leaves a Postgres transaction aborted until it is
    rolled back — without this, every *other* query still to come on the
    same session in this request (e.g. a later service reading a different
    table) would fail too, even if that table is perfectly fine.
    """
    try:
        rows = query()
    except SQLAlchemyError:
        logger.warning(
            "Could not read %s — falling back to mock_data", label, exc_info=True
        )
        if db is not None:
            db.rollback()
        return fallback

    if not rows:
        logger.info("No %s in the database yet — serving mock_data", label)
        return fallback

    return [to_dict(row) for row in rows]


def read_with_fallback(
    *,
    read: Callable[[], ValueT | None],
    fallback: ValueT,
    logger: logging.Logger,
    label: str,
    log_empty: bool = True,
    db: Session | None = None,
) -> ValueT:
    """Same pattern as `load_rows_with_fallback`, for a single optional value.

    Used where a service reads one row (or none) rather than a list — e.g.
    `OverviewService` reading the latest `DailyBrief`. `log_empty` defaults
    to `True` to match `load_rows_with_fallback`; some callers historically
    only logged on error and never logged the empty case, so it can be
    turned off to keep that exact behaviour. See `load_rows_with_fallback`
    for why `db` (optional) matters on the error path.
    """
    try:
        value = read()
    except SQLAlchemyError:
        logger.warning(
            "Could not read %s — falling back to mock_data", label, exc_info=True
        )
        if db is not None:
            db.rollback()
        return fallback

    if value is None:
        if log_empty:
            logger.info("No %s in the database yet — serving mock_data", label)
        return fallback

    return value
