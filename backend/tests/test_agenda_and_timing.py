"""Agenda sanitization and timing labels for meeting intelligence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import User
from app.services.agenda_sanitize import looks_like_recurring_series_dump, sanitize_agenda, strip_html
from app.services.meeting_windows import timing_display_label


def test_strip_html_removes_br_tags():
    assert "<br" not in strip_html("Line one<br>Line two<br/>Line three").lower()
    assert "Line one" in strip_html("Line one<br>Line two")


def test_recurring_dump_not_expanded_into_agenda():
    dump = "\n".join(
        [
            "Aug 30 14:00 Writers Call",
            "Sep 27 14:00 Writers Call",
            "Oct 25 14:00 Writers Call",
            "Nov 29 14:00 Writers Call",
            "Dec 27 14:00 Writers Call",
            "Jan 31 14:00 Writers Call",
            "Feb 28 14:00 Writers Call",
            "Mar 28 14:00 Writers Call",
        ]
    )
    assert looks_like_recurring_series_dump(dump)
    agenda = sanitize_agenda([], description=dump)
    assert len(agenda) <= 2
    assert any("Recurring" in line for line in agenda)
    assert not any("<br" in line.lower() for line in agenda)


def test_html_agenda_sanitized():
    agenda = sanitize_agenda(["Review <b>Q3</b> metrics<br>and risks"])
    assert agenda
    assert all("<" not in item for item in agenda)
    assert any("Q3" in item for item in agenda)


def test_timing_display_includes_relative_and_date():
    user = User(timezone="UTC")
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    assert timing_display_label(now, user, now=now) == "Today · Aug 11"
    assert timing_display_label(now + timedelta(days=1), user, now=now) == "Tomorrow · Aug 12"
    assert timing_display_label(now + timedelta(days=4), user, now=now) == "In 4 days · Aug 15"
    assert timing_display_label(now + timedelta(days=18), user, now=now) == "In 18 days · Aug 29"
