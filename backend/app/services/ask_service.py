from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import User
from app.schemas.ask import AskReportResponse, AskWorkspaceResponse
from app.services import demo_data
from app.services.demo_user import is_demo_user
from app.services.integration_service import IntegrationService


class AskService:
    """Answers executive questions as cited report cards, never as raw chat."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_workspace(self) -> AskWorkspaceResponse:
        # Goes through `IntegrationService` rather than `demo_data.INTEGRATIONS`
        # directly, so `connectedSources` reflects real connection state the
        # moment `integrations` has rows, matching every other cross-service
        # read in this refactor.
        integrations = IntegrationService(self.db, self.user).list_integrations()
        connected = [
            integration["name"]
            for integration in integrations
            if integration["status"] in ("connected", "syncing")
        ]
        return AskWorkspaceResponse(
            suggestions=demo_data.ASK_SUGGESTIONS if is_demo_user(self.user) else [],
            recent=demo_data.ASK_RECENT if is_demo_user(self.user) else [],
            connectedSources=connected,
        )

    def answer(self, question: str) -> AskReportResponse:
        report = self._match(question)
        return AskReportResponse(
            id=f"rep_{uuid4().hex[:12]}",
            question=question,
            answeredAt=datetime.now(timezone.utc).isoformat(),
            **report,
        )

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
