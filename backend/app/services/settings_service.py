from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.settings import (
    NotificationSchema,
    PreferencesSchema,
    PreferencesUpdateRequest,
    SettingsResponse,
)
from app.services import demo_data
from app.services.demo_user import is_demo_user, settings_profile_dict


class SettingsService:
    """Account, briefing and security preferences."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_settings(self) -> SettingsResponse:
        return SettingsResponse(
            profile=settings_profile_dict(self.user),
            preferences=self._preferences(),
            notifications=demo_data.SETTINGS_NOTIFICATIONS if is_demo_user(self.user) else [],
            security=demo_data.SETTINGS_SECURITY if is_demo_user(self.user) else {
                "twoFactorEnabled": False,
                "twoFactorMethod": "Not configured",
                "lastPasswordChange": "Never",
                "sessions": [],
                "apiKeys": [],
            },
            theme=demo_data.SETTINGS_THEME,
            connectedAccounts=(
                demo_data.CONNECTED_ACCOUNTS if is_demo_user(self.user) else []
            ),
        )

    def update_preferences(self, payload: PreferencesUpdateRequest) -> PreferencesSchema:
        changes = payload.model_dump(exclude_none=True)
        # Briefly recommends; the executive acts. Nothing can turn that off.
        changes.pop("autoApproveActions", None)

        if is_demo_user(self.user):
            demo_data.SETTINGS_PREFERENCES.update(changes)
            return PreferencesSchema(**demo_data.SETTINGS_PREFERENCES)

        current = self._preferences()
        current.update(changes)
        current["autoApproveActions"] = False
        self.user.preferences = {
            **(self.user.preferences or {}),
            "briefTime": current["briefTime"],
            "briefDays": current["briefDays"],
            "tone": current["tone"],
            "briefLength": current["briefLength"],
            "focusAreas": current["focusAreas"],
        }
        self.db.commit()
        return PreferencesSchema(**current)

    def set_notification(self, notification_id: str, enabled: bool) -> NotificationSchema:
        for notification in demo_data.SETTINGS_NOTIFICATIONS:
            if notification["id"] == notification_id:
                notification["enabled"] = enabled
                return NotificationSchema(**notification)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found",
        )

    def _preferences(self) -> dict:
        base = dict(demo_data.SETTINGS_PREFERENCES)
        if is_demo_user(self.user):
            return base
        stored = self.user.preferences or {}
        for key in ("briefTime", "briefDays", "tone", "briefLength", "focusAreas"):
            if key in stored:
                base[key] = stored[key]
        base["autoApproveActions"] = False
        return base
