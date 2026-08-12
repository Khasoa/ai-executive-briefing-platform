from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_required, get_db
from app.models import User
from app.schemas.settings import (
    NotificationSchema,
    NotificationUpdateRequest,
    PasswordChangeRequest,
    PasswordChangeResponse,
    PreferencesSchema,
    PreferencesUpdateRequest,
    ProfileUpdateRequest,
    SettingsResponse,
)
from app.schemas.user import UserSchema
from app.services.demo_user import public_user_dict
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsResponse:
    return SettingsService(db, user).get_settings()


@router.patch("/profile", response_model=UserSchema)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> UserSchema:
    """Persist name/role/company/timezone/avatar initials for the authenticated user."""
    SettingsService(db, user).update_profile(payload)
    return UserSchema(**public_user_dict(user))


@router.post("/password", response_model=PasswordChangeResponse)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> PasswordChangeResponse:
    """Change password for password-authenticated users; revokes all refresh tokens."""
    return SettingsService(db, user).change_password(payload)


@router.patch("/preferences", response_model=PreferencesSchema)
def update_preferences(
    payload: PreferencesUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreferencesSchema:
    return SettingsService(db, user).update_preferences(payload)


@router.patch("/notifications/{notification_id}", response_model=NotificationSchema)
def update_notification(
    notification_id: str,
    payload: NotificationUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationSchema:
    return SettingsService(db, user).set_notification(notification_id, payload.enabled)
