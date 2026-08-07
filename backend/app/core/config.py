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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
