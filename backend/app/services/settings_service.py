from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.settings import (
    NotificationSchema,
    PreferencesSchema,
    PreferencesUpdateRequest,
    SettingsResponse,
)
from app.services import mock_data


class SettingsService:
    """Account, briefing and security preferences."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_settings(self) -> SettingsResponse:
        return SettingsResponse(
            profile=mock_data.SETTINGS_PROFILE,
            preferences=mock_data.SETTINGS_PREFERENCES,
            notifications=mock_data.SETTINGS_NOTIFICATIONS,
            security=mock_data.SETTINGS_SECURITY,
            theme=mock_data.SETTINGS_THEME,
            connectedAccounts=mock_data.CONNECTED_ACCOUNTS,
        )

    def update_preferences(self, payload: PreferencesUpdateRequest) -> PreferencesSchema:
        changes = payload.model_dump(exclude_none=True)
        # Briefly recommends; the executive acts. Nothing can turn that off.
        changes.pop("autoApproveActions", None)

        mock_data.SETTINGS_PREFERENCES.update(changes)
        return PreferencesSchema(**mock_data.SETTINGS_PREFERENCES)

    def set_notification(self, notification_id: str, enabled: bool) -> NotificationSchema:
        for notification in mock_data.SETTINGS_NOTIFICATIONS:
            if notification["id"] == notification_id:
                notification["enabled"] = enabled
                return NotificationSchema(**notification)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found",
        )
