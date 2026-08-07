from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.settings import (
    NotificationSchema,
    NotificationUpdateRequest,
    PreferencesSchema,
    PreferencesUpdateRequest,
    SettingsResponse,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsResponse:
    return SettingsService(db, user).get_settings()


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
