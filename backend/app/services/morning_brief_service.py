from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.morning_brief import ChecklistItemSchema, MorningBriefResponse
from app.services import mock_data

# Emails promoted into the brief, in the order an executive should read them.
_BRIEF_EMAIL_IDS = ("em_1", "em_2", "em_3", "em_5", "em_4", "em_6")


class MorningBriefService:
    """Produces the Morning Brief — the product's primary output."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_brief(self) -> MorningBriefResponse:
        return MorningBriefResponse(
            meta=mock_data.BRIEF_META,
            preparedFor=mock_data.USER,
            executiveSummary=mock_data.EXECUTIVE_SUMMARY_TEXT,
            topPriorities=mock_data.PRIORITIES,
            criticalRisks=mock_data.RISKS,
            meetings=self._meetings(),
            clientsNeedingAttention=mock_data.CLIENTS_NEEDING_ATTENTION,
            importantEmails=self._important_emails(),
            suggestedFocus=mock_data.SUGGESTED_FOCUS,
            recommendedDelegation=mock_data.RECOMMENDED_DELEGATION,
            actionChecklist=mock_data.ACTION_CHECKLIST,
            closing=mock_data.CLOSING_ANSWER,
        )

    def regenerate(self) -> MorningBriefResponse:
        """Re-read every connected system and rebuild the brief.

        Only the freshness metadata moves today because the sources are curated;
        once integrations are live this re-runs the assembly pipeline.
        """
        mock_data.BRIEF_META["generatedAt"] = datetime.now(timezone.utc).isoformat()
        mock_data.BRIEF_META["generatedLabel"] = "just now"
        return self.get_brief()

    def set_checklist_item(self, item_id: str, done: bool) -> ChecklistItemSchema:
        for item in mock_data.ACTION_CHECKLIST:
            if item["id"] == item_id:
                item["done"] = done
                return ChecklistItemSchema(**item)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist item '{item_id}' not found",
        )

    @staticmethod
    def _meetings() -> list[dict]:
        return [
            {
                "id": meeting["id"],
                "time": meeting["startTime"],
                "title": meeting["title"],
                "attendees": [attendee["name"] for attendee in meeting["attendees"]],
                "prepStatus": meeting["prepStatus"],
                "note": meeting["prepReason"],
            }
            for meeting in mock_data.MEETINGS
        ]

    @staticmethod
    def _important_emails() -> list[dict]:
        by_id = {email["id"]: email for email in mock_data.EMAILS}
        return [
            {
                "id": email["id"],
                "sender": email["sender"]["name"],
                "subject": email["subject"],
                "summary": email["aiSummary"],
                "priority": email["priority"],
                "waitingSince": email["timeLabel"],
            }
            for email_id in _BRIEF_EMAIL_IDS
            if (email := by_id.get(email_id))
        ]
