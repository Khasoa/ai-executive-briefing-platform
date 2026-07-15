from sqlalchemy.orm import Session

from app.schemas.settings import SettingsResponse
from app.services import mock_data


class SettingsService:
    """Provides user settings and integration status."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_settings(self) -> SettingsResponse:
        # Future: query User and Integration models from database
        return SettingsResponse(
            user=mock_data.USER,
            sections=mock_data.SETTINGS_SECTIONS,
            integrations=mock_data.INTEGRATIONS,
        )
