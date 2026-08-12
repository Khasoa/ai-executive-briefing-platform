import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AskReport, User
from app.schemas.ask import AskReportResponse, AskWorkspaceResponse
from app.services import demo_data
from app.services.demo_user import is_demo_user
from app.services.integration_service import IntegrationService
from app.services.mapping_utils import relative_time_label, stringify_id

logger = logging.getLogger("briefly.ask")


class AskService:
    """Answers executive questions as cited report cards, never as raw chat."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_workspace(self) -> AskWorkspaceResponse:
        integrations = IntegrationService(self.db, self.user).list_integrations()
        connected = [
            integration["name"]
            for integration in integrations
            if integration["status"] in ("connected", "syncing")
        ]
        recent = self._recent_questions()
        return AskWorkspaceResponse(
            suggestions=demo_data.ASK_SUGGESTIONS if is_demo_user(self.user) else [],
            recent=recent,
            connectedSources=connected,
        )

    def answer(self, question: str) -> AskReportResponse:
        from app.services.ai_service import AIService

        report = AIService(self.db, self.user).answer_question(question)
        if report is None:
            report = self._match(question)

        answered_at = datetime.now(timezone.utc)
        row = self._persist_report(question, report, answered_at)
        report_id = stringify_id(row.id) if row is not None else f"rep_{answered_at.strftime('%H%M%S%f')}"

        return AskReportResponse(
            id=report_id,
            question=question,
            answeredAt=answered_at.isoformat(),
            **report,
        )

    def _persist_report(
        self,
        question: str,
        report: dict,
        answered_at: datetime,
    ) -> AskReport | None:
        try:
            row = AskReport(
                user_id=self.user.id,
                question=question,
                summary=report["summary"],
                confidence=report["confidence"],
                sections=report["sections"],
                citations=report["citations"],
                follow_ups=report["followUps"],
                answered_at=answered_at,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return row
        except SQLAlchemyError:
            logger.warning("Could not persist Ask report — continuing without history", exc_info=True)
            self.db.rollback()
            return None

    def _recent_questions(self) -> list[dict]:
        try:
            rows = (
                self.db.query(AskReport)
                .filter(AskReport.user_id == self.user.id)
                .order_by(AskReport.answered_at.desc())
                .limit(10)
                .all()
            )
        except SQLAlchemyError:
            logger.warning("Could not read Ask history", exc_info=True)
            rows = []

        if rows:
            return [
                {
                    "id": stringify_id(row.id),
                    "question": row.question,
                    "askedAt": relative_time_label(row.answered_at),
                }
                for row in rows
            ]

        if is_demo_user(self.user):
            return demo_data.ASK_RECENT
        return []

    @staticmethod
    def _match(question: str) -> dict:
        """Exact match first, then a loose keyword match, then the generic report."""
        if question in demo_data.ASK_REPORTS:
            return demo_data.ASK_REPORTS[question]

        normalised = question.lower().strip().rstrip("?.")
        for known, report in demo_data.ASK_REPORTS.items():
            if normalised in known.lower() or known.lower().rstrip("?.") in normalised:
                return report

        keywords = {
            "prioriti": "What should I prioritize today?",
            "meeting": "Prepare me for today's meetings.",
            "prepare": "Prepare me for today's meetings.",
            "risk": "Which deals are most at risk?",
            "deal": "Which deals are most at risk?",
            "pipeline": "Which deals are most at risk?",
            "chang": "What changed since yesterday?",
            "yesterday": "What changed since yesterday?",
            "draft": "Draft a follow-up email for Meridian Labs.",
            "email": "Draft a follow-up email for Meridian Labs.",
            "meridian": "Draft a follow-up email for Meridian Labs.",
            "block": "Where is my team blocked on me?",
            "team": "Where is my team blocked on me?",
        }
        for keyword, known in keywords.items():
            if keyword in normalised:
                return demo_data.ASK_REPORTS[known]

        return demo_data.DEFAULT_ASK_REPORT
