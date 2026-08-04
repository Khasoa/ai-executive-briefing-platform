from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.ask import AskReportResponse, AskWorkspaceResponse
from app.services import mock_data


class AskService:
    """Answers executive questions as cited report cards, never as raw chat."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_workspace(self) -> AskWorkspaceResponse:
        connected = [
            integration["name"]
            for integration in mock_data.INTEGRATIONS
            if integration["status"] in ("connected", "syncing")
        ]
        return AskWorkspaceResponse(
            suggestions=mock_data.ASK_SUGGESTIONS,
            recent=mock_data.ASK_RECENT,
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
        if question in mock_data.ASK_REPORTS:
            return mock_data.ASK_REPORTS[question]

        normalised = question.lower().strip().rstrip("?.")
        for known, report in mock_data.ASK_REPORTS.items():
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
                return mock_data.ASK_REPORTS[known]

        return mock_data.DEFAULT_ASK_REPORT
