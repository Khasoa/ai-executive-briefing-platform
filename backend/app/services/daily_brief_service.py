import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import DailyBrief
from app.schemas.daily_brief import DailyBriefSchema


class DailyBriefService:
    """Reads and writes the `daily_briefs` table.

    This is the first service in Briefly that talks to PostgreSQL for real,
    rather than reading `demo_data`. It is used by `OverviewService` for three
    fields (`summary`, `priorities`, `risks`) and by the standalone
    `GET /daily-brief/latest` endpoint, which exposes the raw table directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_brief(
        self,
        *,
        summary: str,
        priorities: list[dict],
        risks: list[dict],
        recommendations: list[dict],
        executive_score: int,
        generated_at: datetime | None = None,
    ) -> DailyBriefSchema:
        """Insert one generated briefing and return it in API shape."""
        brief = DailyBrief(
            generated_at=generated_at or datetime.now(timezone.utc),
            summary=summary,
            priorities=priorities,
            risks=risks,
            recommendations=recommendations,
            executive_score=executive_score,
        )
        self.db.add(brief)
        self.db.commit()
        self.db.refresh(brief)
        return self._to_schema(brief)

    def get_latest_brief(self) -> DailyBriefSchema | None:
        """Return the most recently generated brief, or `None` if the table is empty.

        SQLAlchemy retrieval: this issues
        `SELECT * FROM daily_briefs ORDER BY generated_at DESC LIMIT 1` through
        the ORM (`.order_by(...).first()`), then maps the single row onto
        `DailyBriefSchema`. There is no caching layer yet, so "latest" is
        always a live read — every call to `OverviewService.get_overview()`
        re-queries this table.
        """
        brief = self.db.query(DailyBrief).order_by(DailyBrief.generated_at.desc()).first()
        return self._to_schema(brief) if brief else None

    def get_brief_by_id(self, brief_id: str) -> DailyBriefSchema | None:
        """Primary-key lookup for a single brief (e.g. a future brief-history page)."""
        try:
            brief_uuid = uuid.UUID(brief_id)
        except ValueError:
            return None

        brief = self.db.get(DailyBrief, brief_uuid)
        return self._to_schema(brief) if brief else None

    @staticmethod
    def _to_schema(brief: DailyBrief) -> DailyBriefSchema:
        return DailyBriefSchema(
            id=str(brief.id),
            generatedAt=brief.generated_at,
            summary=brief.summary,
            priorities=brief.priorities,
            risks=brief.risks,
            recommendations=brief.recommendations,
            executiveScore=brief.executive_score,
            createdAt=brief.created_at,
        )
