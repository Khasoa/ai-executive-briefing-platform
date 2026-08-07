import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import DailyBrief, User
from app.schemas.daily_brief import DailyBriefSchema


class DailyBriefService:
    """Reads and writes the `daily_briefs` table, scoped to one user."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

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
            user_id=self.user.id,
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
        """Return the most recently generated brief for this user, or `None`."""
        brief = (
            self.db.query(DailyBrief)
            .filter(DailyBrief.user_id == self.user.id)
            .order_by(DailyBrief.generated_at.desc())
            .first()
        )
        return self._to_schema(brief) if brief else None

    def get_brief_by_id(self, brief_id: str) -> DailyBriefSchema | None:
        """Primary-key lookup for a single brief owned by this user."""
        try:
            brief_uuid = uuid.UUID(brief_id)
        except ValueError:
            return None

        brief = (
            self.db.query(DailyBrief)
            .filter(DailyBrief.id == brief_uuid, DailyBrief.user_id == self.user.id)
            .first()
        )
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
