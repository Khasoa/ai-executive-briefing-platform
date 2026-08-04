from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
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
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    return SettingsService(db).get_settings()


@router.patch("/preferences", response_model=PreferencesSchema)
def update_preferences(
    payload: PreferencesUpdateRequest,
    db: Session = Depends(get_db),
) -> PreferencesSchema:
    return SettingsService(db).update_preferences(payload)


@router.patch("/notifications/{notification_id}", response_model=NotificationSchema)
def update_notification(
    notification_id: str,
    payload: NotificationUpdateRequest,
    db: Session = Depends(get_db),
) -> NotificationSchema:
    return SettingsService(db).set_notification(notification_id, payload.enabled)
