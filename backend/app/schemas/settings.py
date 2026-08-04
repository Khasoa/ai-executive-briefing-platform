from pydantic import BaseModel


class ProfileSchema(BaseModel):
    fullName: str
    role: str
    company: str
    email: str
    phone: str
    timezone: str
    avatar: str


class PreferencesSchema(BaseModel):
    briefTime: str
    briefDays: list[str]
    tone: str
    toneOptions: list[str]
    briefLength: str
    briefLengthOptions: list[str]
    focusAreas: list[str]
    focusAreaOptions: list[str]
    autoApproveActions: bool


class PreferencesUpdateRequest(BaseModel):
    briefTime: str | None = None
    briefDays: list[str] | None = None
    tone: str | None = None
    briefLength: str | None = None
    focusAreas: list[str] | None = None
    autoApproveActions: bool | None = None


class NotificationSchema(BaseModel):
    id: str
    label: str
    description: str
    channel: str
    enabled: bool


class NotificationUpdateRequest(BaseModel):
    enabled: bool


class SessionSchema(BaseModel):
    id: str
    device: str
    location: str
    lastActive: str
    current: bool


class ApiKeySchema(BaseModel):
    id: str
    label: str
    prefix: str
    createdAt: str
    lastUsed: str


class SecuritySchema(BaseModel):
    twoFactorEnabled: bool
    twoFactorMethod: str
    lastPasswordChange: str
    sessions: list[SessionSchema]
    apiKeys: list[ApiKeySchema]


class ThemeSchema(BaseModel):
    mode: str
    modeOptions: list[str]
    density: str
    densityOptions: list[str]
    accent: str
    accentOptions: list[str]
    reducedMotion: bool


class ConnectedAccountSchema(BaseModel):
    id: str
    provider: str
    detail: str
    status: str
    connectedAt: str | None = None


class SettingsResponse(BaseModel):
    profile: ProfileSchema
    preferences: PreferencesSchema
    notifications: list[NotificationSchema]
    security: SecuritySchema
    theme: ThemeSchema
    connectedAccounts: list[ConnectedAccountSchema]
