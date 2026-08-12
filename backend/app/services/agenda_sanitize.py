"""Sanitize calendar descriptions / agendas for concise meeting intelligence cards."""

from __future__ import annotations

import html
import re
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>", re.I)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_DATEISH_RE = re.compile(
    r"\b("
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}"
    r"|\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?"
    r"|20\d{2}-\d{2}-\d{2}"
    r")\b",
    re.I,
)
_RECURRING_HINT = re.compile(
    r"(recurring|repeats?|every\s+(week|month|day)|rrule|occurrence)",
    re.I,
)
_SERIES_LINE = re.compile(
    r"^("
    r".*\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}.*\d{1,2}:\d{2}"
    r"|.*→.*|"
    r".*\|\s*\d{1,2}:\d{2}"
    r")$",
    re.I,
)


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_like_recurring_series_dump(text: str) -> bool:
    """True when description looks like a dumped list of future occurrences."""
    cleaned = strip_html(text)
    if not cleaned:
        return False
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    if len(lines) >= 8:
        dateish = sum(1 for ln in lines if _DATEISH_RE.search(ln) or _SERIES_LINE.match(ln))
        if dateish >= 5:
            return True
    if _RECURRING_HINT.search(cleaned) and cleaned.count("\n") >= 10:
        return True
    return False


def sanitize_agenda(
    agenda: Any,
    *,
    max_items: int = 8,
    description: str | None = None,
) -> list[str]:
    """Normalize agenda lines: no raw HTML, no recurring-series dumps."""
    raw_lines: list[str] = []
    if isinstance(agenda, list):
        for item in agenda:
            if item is None:
                continue
            raw_lines.append(str(item))
    elif isinstance(agenda, str) and agenda.strip():
        raw_lines.append(agenda)

    if description:
        raw_lines.extend(strip_html(description).splitlines())

    joined = "\n".join(raw_lines)
    if looks_like_recurring_series_dump(joined):
        # Keep a short note instead of dozens of future dates.
        return ["Recurring series — agenda details omitted for this occurrence."]

    out: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        cleaned = strip_html(line)
        for piece in cleaned.splitlines():
            piece = piece.strip(" •-\t")
            if not piece:
                continue
            # Drop pure occurrence-list rows.
            if _SERIES_LINE.match(piece) and _DATEISH_RE.search(piece):
                continue
            if "<" in piece and ">" in piece:
                piece = strip_html(piece)
            key = piece.lower()
            if key in seen:
                continue
            seen.add(key)
            if len(piece) > 280:
                piece = piece[:277].rstrip() + "…"
            out.append(piece)
            if len(out) >= max_items:
                return out
    return out


def detect_recurring(event: dict[str, Any] | None = None, intelligence: dict | None = None) -> bool:
    event = event or {}
    intelligence = intelligence or {}
    google = intelligence.get("google") if isinstance(intelligence, dict) else {}
    google = google or {}
    if event.get("recurringEventId") or google.get("recurringEventId"):
        return True
    if event.get("recurrence") or google.get("recurrence"):
        return True
    text = f"{event.get('summary') or ''} {event.get('description') or ''}"
    return bool(_RECURRING_HINT.search(text))
