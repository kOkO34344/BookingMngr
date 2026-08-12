"""Environment-driven application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---------------------------------------------------------------
    app_name: str = "BookingMngr API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # --- Database ----------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://bookingmngr:bookingmngr@localhost:5432/bookingmngr"
    )
    db_echo: bool = False

    # --- Auth --------------------------------------------------------------
    secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days, internal tool

    # Bootstrap owner account (created by `python -m app.db.init_db`).
    owner_username: str = "owner"
    owner_password: str = "changeme"
    owner_email: str = "owner@example.com"
    default_organization_name: str = "My Properties"

    # --- CORS --------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Domain defaults ---------------------------------------------------
    default_currency: str = "EUR"
    default_timezone: str = "Europe/Sofia"
    default_cleaning_duration_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
