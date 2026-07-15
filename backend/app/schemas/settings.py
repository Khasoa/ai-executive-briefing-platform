from pydantic import BaseModel

from app.schemas.user import UserSchema


class SettingsSectionSchema(BaseModel):
    title: str
    description: str


class IntegrationSchema(BaseModel):
    provider: str
    status: str
    description: str


class SettingsResponse(BaseModel):
    user: UserSchema
    sections: list[SettingsSectionSchema]
    integrations: list[IntegrationSchema]
