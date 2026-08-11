from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import RefreshToken, User
from app.schemas.settings import (
    NotificationSchema,
    PasswordChangeRequest,
    PasswordChangeResponse,
    PreferencesSchema,
    PreferencesUpdateRequest,
    ProfileSchema,
    ProfileUpdateRequest,
    SettingsResponse,
)
from app.schemas.user import UserSchema
from app.services import demo_data
from app.services.demo_user import is_demo_user, public_user_dict, settings_profile_dict


class SettingsService:
    """Account, briefing and security preferences."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def get_settings(self) -> SettingsResponse:
        has_password = bool(self.user.hashed_password)
        if is_demo_user(self.user):
            security = dict(demo_data.SETTINGS_SECURITY)
            security["hasPassword"] = has_password
            security["passwordChangeAvailable"] = has_password
        else:
            security = {
                "twoFactorEnabled": False,
                "twoFactorMethod": "Not configured",
                "lastPasswordChange": "Never",
                "hasPassword": has_password,
                "passwordChangeAvailable": has_password,
                "sessions": [],
                "apiKeys": [],
            }
        return SettingsResponse(
            profile=settings_profile_dict(self.user),
            preferences=self._preferences(),
            notifications=demo_data.SETTINGS_NOTIFICATIONS if is_demo_user(self.user) else [],
            security=security,
            theme=demo_data.SETTINGS_THEME,
            connectedAccounts=(
                demo_data.CONNECTED_ACCOUNTS if is_demo_user(self.user) else []
            ),
        )

    def update_profile(self, payload: ProfileUpdateRequest) -> ProfileSchema:
        changes = payload.model_dump(exclude_none=True)
        if not changes:
            return ProfileSchema(**settings_profile_dict(self.user))

        if "fullName" in changes:
            full_name = changes["fullName"].strip()
            if not full_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Full name cannot be empty",
                )
            self.user.full_name = full_name
            self.user.name = full_name.split()[0]
            # Refresh initials only when avatar was not explicitly set in this request.
            if "avatar" not in changes:
                initials = "".join(part[0] for part in full_name.split()[:2]).upper() or "BR"
                self.user.avatar = initials[:10]

        if "role" in changes:
            self.user.role = changes["role"].strip() or self.user.role
        if "company" in changes:
            self.user.company = changes["company"].strip()
        if "timezone" in changes:
            self.user.timezone = changes["timezone"].strip() or "UTC"
        if "avatar" in changes:
            avatar = changes["avatar"].strip().upper()[:10]
            if not avatar:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Avatar initials cannot be empty",
                )
            self.user.avatar = avatar

        if is_demo_user(self.user):
            # Keep demo curated SETTINGS_PROFILE labels in sync for phone/timezone display.
            demo_data.SETTINGS_PROFILE["fullName"] = self.user.full_name
            demo_data.SETTINGS_PROFILE["role"] = self.user.role
            demo_data.SETTINGS_PROFILE["company"] = self.user.company
            demo_data.SETTINGS_PROFILE["avatar"] = self.user.avatar

        self.db.commit()
        self.db.refresh(self.user)
        return ProfileSchema(**settings_profile_dict(self.user))

    def change_password(self, payload: PasswordChangeRequest) -> PasswordChangeResponse:
        if not self.user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This account signs in with Google and has no password. "
                    "Profile edits do not require a password."
                ),
            )
        if not verify_password(payload.currentPassword, self.user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        new_password = payload.newPassword.strip()
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password must be at least 8 characters",
            )
        if verify_password(new_password, self.user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password must be different from the current password",
            )

        self.user.hashed_password = hash_password(new_password)
        now = datetime.now(timezone.utc)
        tokens = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == self.user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .all()
        )
        for token in tokens:
            token.revoked_at = now
        self.db.commit()
        return PasswordChangeResponse()

    def public_user(self) -> UserSchema:
        return UserSchema(**public_user_dict(self.user))

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
