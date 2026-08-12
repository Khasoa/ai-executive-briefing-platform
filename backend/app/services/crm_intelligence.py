"""Derive executive CRM signals from synced Opportunity rows — no fabrication."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


def derive_crm_signals(opportunities: list[dict[str, Any]], *, today: date | None = None) -> dict[str, Any]:
    """Build structured signals from opportunity dicts (CRMService shape)."""
    today = today or datetime.now(timezone.utc).date()
    at_risk = []
    stale = []
    upcoming_closes = []
    follow_up = []
    high_value = []

    for opp in opportunities:
        company = opp.get("company") or "Opportunity"
        value = int(opp.get("value") or 0)
        risk = (opp.get("riskLevel") or "").lower()
        stage = opp.get("stage") or ""
        close_raw = opp.get("closeDate") or ""
        close = _parse_close_label(close_raw)
        last = opp.get("lastInteraction") or {}
        last_time = (last.get("time") or "").lower()
        sources = list(opp.get("sources") or [])
        if "GoHighLevel" not in sources and sources:
            # Still attribute when GHL is present in nested metadata.
            pass
        source = "GoHighLevel" if "GoHighLevel" in sources or not sources else sources[0]

        item = {
            "id": opp.get("id"),
            "company": company,
            "stage": stage,
            "value": value,
            "closeDate": close_raw,
            "riskLevel": risk,
            "source": source,
            "detail": (opp.get("aiSummary") or last.get("summary") or stage)[:240],
        }

        if risk in ("critical", "high"):
            at_risk.append({**item, "signal": "at_risk"})
        if value >= 100_000:
            high_value.append({**item, "signal": "high_value"})
        if close and 0 <= (close - today).days <= 14:
            upcoming_closes.append({**item, "signal": "upcoming_close"})
        if _looks_stale(last_time, close, today):
            stale.append({**item, "signal": "stale"})
        if risk in ("critical", "high") or "follow" in (opp.get("recommendedAction") or "").lower():
            follow_up.append({**item, "signal": "follow_up"})

    return {
        "dealsAtRisk": at_risk[:12],
        "staleOpportunities": stale[:12],
        "upcomingCloses": upcoming_closes[:12],
        "followUpRequired": follow_up[:12],
        "highValueNeedingAttention": [
            h for h in high_value if h.get("riskLevel") in ("critical", "high", "medium")
        ][:12],
    }


def _looks_stale(last_time: str, close: date | None, today: date) -> bool:
    if "days ago" in last_time:
        try:
            days = int(last_time.split()[0])
            if days >= 7:
                return True
        except ValueError:
            pass
    if close and close < today - timedelta(days=1):
        return True
    return False


def _parse_close_label(label: str) -> date | None:
    """Parse CRMService close labels like 'Aug 7, 2026'."""
    if not label:
        return None
    try:
        return datetime.strptime(label, "%b %d, %Y").date()
    except ValueError:
        return None
