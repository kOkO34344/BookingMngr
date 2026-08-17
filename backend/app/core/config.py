"""Environment-driven application configuration."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Placeholders that are fine locally and must never reach a public host.
INSECURE_SECRET_KEY = "change-me-in-production"
INSECURE_OWNER_PASSWORD = "changeme"


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
    secret_key: str = Field(default=INSECURE_SECRET_KEY)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days, internal tool

    # Bootstrap owner account (created by `python -m app.db.init_db`).
    owner_username: str = "owner"
    owner_password: str = INSECURE_OWNER_PASSWORD
    owner_email: str = "owner@example.com"
    default_organization_name: str = "My Properties"

    # --- CORS --------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Domain defaults ---------------------------------------------------
    default_currency: str = "EUR"
    default_timezone: str = "Europe/Sofia"
    default_cleaning_duration_minutes: int = 60

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def _refuse_insecure_production(self) -> "Settings":
        """Fail at boot rather than serve a guessable login on the internet.

        A signing key left at its default lets anyone mint a valid token, and
        the bootstrap password is published in .env.example. Both are harmless
        locally, so this only fires when ENVIRONMENT=production.
        """
        if not self.is_production:
            return self

        problems = []
        if self.secret_key == INSECURE_SECRET_KEY:
            problems.append(
                "SECRET_KEY is still the default. Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if self.owner_password == INSECURE_OWNER_PASSWORD:
            problems.append("OWNER_PASSWORD is still the default 'changeme'.")
        if problems:
            raise ValueError(
                "Refusing to start in production:\n- " + "\n- ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
