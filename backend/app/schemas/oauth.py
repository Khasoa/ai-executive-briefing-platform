from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.auth import TokenResponse


class OAuthAuthorizeResponse(BaseModel):
    provider: str
    authorizationUrl: str
    state: str


class OAuthTicketExchangeRequest(BaseModel):
    ticket: str = Field(min_length=20, max_length=512)


class OAuthConnectionStatus(BaseModel):
    provider: str
    connected: bool
    configured: bool
    account: str | None = None
    subject: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connectedAt: datetime | None = None


class OAuthProviderTokenResponse(BaseModel):
    provider: str
    accessToken: str
    expiresSkewSeconds: int = 60


# Re-export for OpenAPI clarity on ticket exchange.
OAuthTokenResponse = TokenResponse
