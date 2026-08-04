from typing import Literal

from pydantic import BaseModel

IntegrationStatus = Literal["connected", "syncing", "not-connected", "error"]


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
