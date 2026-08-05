import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Opportunity
from app.schemas.crm import CRMResponse, OpportunitySchema
from app.services import mock_data

logger = logging.getLogger("briefly.crm")

# Only surface deals an executive can actually influence this week.
_ATTENTION_LEVELS = ("critical", "high")


class CRMService:
    """Filters the pipeline down to opportunities needing executive attention.

    Phase 4 of the PostgreSQL migration: opportunities are read from the
    `opportunities` table when rows exist there, falling back to
    `mock_data.OPPORTUNITIES` otherwise — including when the database itself
    is unreachable. Same fallback pattern as `MeetingService` and
    `InboxService`; see `_load_opportunities()` for the mechanics.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_pipeline(self) -> CRMResponse:
        opportunities = self._load_opportunities()
        needing_attention = [o for o in opportunities if o["riskLevel"] in _ATTENTION_LEVELS]

        return CRMResponse(
            summary={
                "pipelineValue": sum(o["value"] for o in opportunities),
                "weightedValue": round(
                    sum(o["value"] * o["probability"] / 100 for o in opportunities)
                ),
                "needingAttention": len(needing_attention),
                "closingThisMonth": sum(1 for o in opportunities if "Aug" in o["closeDate"]),
                "headline": self._headline(needing_attention),
            },
            opportunities=opportunities,
        )

    def get_opportunity(self, opportunity_id: str) -> OpportunitySchema:
        # Reuses `_load_opportunities()` rather than a dedicated lookup so a
        # single request never mixes a database-backed list with a
        # mock-backed one, matching `MeetingService.get_meeting()`.
        for opportunity in self._load_opportunities():
            if opportunity["id"] == opportunity_id:
                return OpportunitySchema(**opportunity)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity '{opportunity_id}' not found",
        )

    def _load_opportunities(self) -> list[dict]:
        """Read every opportunity from PostgreSQL, falling back to `mock_data.OPPORTUNITIES`.

        Fallback strategy: the same two situations as `MeetingService` and
        `InboxService` land here — the table is reachable but empty (nothing
        seeded yet), or the database itself is unreachable (not migrated,
        connection dropped, credentials wrong). Both serve the curated
        pipeline instead of an empty or broken response, so a database
        problem degrades the CRM page rather than breaking it. An empty
        result is logged at info level (a normal, expected state before
        seeding); a database error is logged as a warning (something is
        actually wrong).
        """
        try:
            rows = self.db.query(Opportunity).order_by(Opportunity.close_date.asc()).all()
        except SQLAlchemyError:
            logger.warning(
                "Could not read opportunities — falling back to mock_data", exc_info=True
            )
            return mock_data.OPPORTUNITIES

        if not rows:
            logger.info("No opportunities in the database yet — serving mock_data")
            return mock_data.OPPORTUNITIES

        return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(opportunity: Opportunity) -> dict:
        """Map an `Opportunity` row onto the exact dict shape `OpportunitySchema` expects.

        Most fields map onto columns one-to-one. `sources` has no dedicated
        column — like `Meeting.intelligence`, it rides inside the existing
        `last_interaction` JSONB blob as an extra key, alongside `type`,
        `summary` and `time`, rather than requiring a schema change.
        """
        last_interaction = opportunity.last_interaction or {}
        close_date = opportunity.close_date
        return {
            "id": str(opportunity.id),
            "company": opportunity.company,
            "logo": opportunity.logo,
            "industry": opportunity.industry,
            "stage": opportunity.stage,
            "value": round(opportunity.value),
            "probability": opportunity.probability,
            "owner": opportunity.owner,
            "closeDate": CRMService._format_close_date(close_date),
            "riskLevel": opportunity.risk_level,
            "lastInteraction": {
                "type": last_interaction.get("type", ""),
                "summary": last_interaction.get("summary", ""),
                "time": last_interaction.get("time", ""),
            },
            "aiSummary": opportunity.ai_summary,
            "recommendedAction": opportunity.recommended_action,
            "signals": opportunity.signals,
            "sources": last_interaction.get("sources", []),
        }

    @staticmethod
    def _format_close_date(close_date) -> str:
        if close_date is None:
            return ""
        # Matches the mock data's "Aug 7, 2026" style, which `closingThisMonth`
        # below relies on via a plain substring check ("Aug" in closeDate).
        return f"{close_date.strftime('%b')} {close_date.day}, {close_date.year}"

    @staticmethod
    def _headline(needing_attention: list[dict]) -> str:
        if not needing_attention:
            return "No opportunities need executive attention today."

        exposure = sum(o["value"] for o in needing_attention)
        lead = max(needing_attention, key=lambda o: o["value"])
        formatted = (
            f"${exposure / 1_000_000:.1f}M" if exposure >= 1_000_000 else f"${exposure // 1_000}K"
        )
        return (
            f"{len(needing_attention)} opportunities worth {formatted} need you. "
            f"{lead['company']} is the one that moves the quarter."
        )
