from typing import Literal

from pydantic import BaseModel, Field

# Additive statuses: configured = env/API-key ready (OpenAI/n8n).
IntegrationStatus = Literal[
    "connected",
    "syncing",
    "not-connected",
    "error",
    "configured",
]

AuthType = Literal["oauth", "api_key", "webhook", "derived"]


class IntegrationMetricSchema(BaseModel):
    label: str
    value: str


class IntegrationSchema(BaseModel):
    id: str
    name: str
    category: str
    description: str
    status: IntegrationStatus
    account: str | None = None
    lastSync: str | None = None
    lastSyncLabel: str
    scopes: list[str]
    metrics: list[IntegrationMetricSchema]
    poweredBy: str
    # Additive fields — older clients ignore unknown JSON; OpenAPI documents them.
    authType: AuthType = "oauth"
    statusDetail: str | None = None
    canSync: bool = True
    canConnect: bool = True
    canDisconnect: bool = False
    canCheck: bool = False


class SyncEventSchema(BaseModel):
    id: str
    integrationId: str
    integration: str
    event: str
    status: Literal["success", "running", "warning", "error"]
    time: str
    detail: str


class IntegrationsResponse(BaseModel):
    connectedCount: int
    totalCount: int
    integrations: list[IntegrationSchema]
    syncHistory: list[SyncEventSchema]


class IntegrationCheckResponse(BaseModel):
    id: str
    configured: bool
    status: IntegrationStatus
    message: str
    authType: AuthType
    # Never includes secrets or API keys.
    details: dict[str, str | bool | int] = Field(default_factory=dict)
