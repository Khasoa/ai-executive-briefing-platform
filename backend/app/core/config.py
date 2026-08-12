from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Briefly API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (PostgreSQL on Railway)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/briefly"

    # CORS — comma-separated in .env, list in code
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Logging
    log_level: str = "INFO"

    # Authentication
    # When auth_required is False (portfolio / demo default), missing Bearer
    # tokens resolve to the demo user so the product behaves as before.
    # When True, every protected route requires a valid access token.
    auth_required: bool = False
    secret_key: str = "dev-only-change-me-briefly-auth-key!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    demo_user_password: str = "briefly-demo"

    # Google OAuth + Calendar + Gmail sync
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/oauth/google/callback"
    # When set, OAuth callback 302s here with ?ticket=… instead of returning JSON.
    oauth_success_redirect: str = ""
    oauth_state_expire_minutes: int = 10
    oauth_ticket_expire_minutes: int = 2
    oauth_http_timeout_seconds: float = 10.0
    # Public HTTPS URL Google calls for Calendar push notifications (optional).
    google_calendar_webhook_url: str = ""
    google_calendar_sync_lookback_days: int = 7
    google_calendar_sync_lookahead_days: int = 90
    # Gmail Pub/Sub topic for users.watch (optional), e.g. projects/x/topics/gmail
    gmail_pubsub_topic: str = ""
    gmail_sync_lookback_days: int = 14
    gmail_sync_max_messages: int = 500

    # OpenAI (Responses API). Empty key → curated/demo failover everywhere.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_embed_model: str = "text-embedding-3-small"
    openai_timeout_seconds: float = 30.0

    # Notion OAuth + workspace sync. Empty → portfolio demo without Notion API.
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_redirect_uri: str = "http://localhost:8000/auth/oauth/notion/callback"

    # GoHighLevel OAuth + opportunity sync. Empty → portfolio demo without GHL API.
    ghl_client_id: str = ""
    ghl_client_secret: str = ""
    ghl_redirect_uri: str = "http://localhost:8000/auth/oauth/gohighlevel/callback"

    # monday.com OAuth + board item sync. Empty → portfolio demo without monday API.
    monday_client_id: str = ""
    monday_client_secret: str = ""
    monday_redirect_uri: str = "http://localhost:8000/auth/oauth/monday/callback"

    # ClickUp OAuth + task sync. Empty → portfolio demo without ClickUp API.
    clickup_client_id: str = ""
    clickup_client_secret: str = ""
    clickup_redirect_uri: str = "http://localhost:8000/auth/oauth/clickup/callback"

    # n8n orchestration. Empty → webhook endpoints return 503.
    n8n_webhook_secret: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
