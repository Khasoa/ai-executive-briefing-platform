from sqlalchemy.orm import Session

from app.schemas.crm import CRMResponse
from app.services import mock_data

# Only surface deals an executive can actually influence this week.
_ATTENTION_LEVELS = ("critical", "high")


class CRMService:
    """Filters the pipeline down to opportunities needing executive attention."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_pipeline(self) -> CRMResponse:
        opportunities = mock_data.OPPORTUNITIES
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
