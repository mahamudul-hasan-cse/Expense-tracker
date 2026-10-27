from functools import lru_cache
from typing import Literal, Optional

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only usable outside production; production must set SECRET_KEY explicitly
DEV_SECRET_KEY = "dev-insecure-secret-key-change-me-in-production"
DEV_DATABASE_URL = "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent"
# Documented default (shortlist candidate A); ASSISTANT_MODEL overrides it
DEFAULT_ASSISTANT_MODEL = "anthropic/claude-haiku-5.5"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    # "Today", due dates and future-date checks use this zone, not the server's
    app_timezone: str = "Asia/Dhaka"
    database_url: str = DEV_DATABASE_URL

    # Comma-separated origins allowed to call the API from a browser.
    # CORS_ORIGINS is the older name and still accepted.
    allowed_origins: str = Field(
        "http://localhost:3000",
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )

    # Auth
    secret_key: str = DEV_SECRET_KEY
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Refresh cookie flags. The frontend proxies /api/* to this backend, so the
    # cookie is first-party and "strict" works. cookie_secure defaults to on in
    # production (HTTPS) and off elsewhere (plain-http localhost).
    cookie_secure: Optional[bool] = None
    cookie_samesite: Literal["lax", "strict", "none"] = "strict"

    # Rate limiting (per client IP, slowapi syntax e.g. "120/minute")
    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"
    rate_limit_auth: str = "5/minute;20/hour"
    # Failed logins per account (email), independent of client IP
    rate_limit_login_failures: str = "10/hour"
    # memory:// is per-process; use e.g. redis://host:6379 with several workers/instances
    rate_limit_storage_uri: str = "memory://"

    # AI assistant (OpenRouter). Disabled when the key is empty; the app still runs.
    # SecretStr keeps the key out of reprs and logs.
    openrouter_api_key: SecretStr = SecretStr("")
    # Empty = the documented default (DEFAULT_ASSISTANT_MODEL); production picks from the eval
    assistant_model: str = ""
    assistant_fallback_models: str = ""  # comma-separated
    assistant_app_url: str = "http://localhost:3000"
    assistant_app_name: str = "Wallet Agent"
    assistant_require_zdr: bool = True
    assistant_daily_message_limit: int = 20
    assistant_global_daily_budget_usd: float = 1.0
    # Includes hidden reasoning tokens (Haiku 5.5 used ~150-460 of them per answer in testing)
    assistant_max_output_tokens: int = 1600
    # OpenRouter `reasoning.effort` (none|minimal|low|medium|high); empty = the model's default.
    # Set from the A4 latency measurement; reasoning text is never sent back to the app.
    assistant_reasoning_effort: Literal["", "none", "minimal", "low", "medium", "high"] = ""
    assistant_max_tool_calls: int = 8
    assistant_history_messages: int = 20
    assistant_timeout_seconds: float = 60.0

    @property
    def assistant_models(self) -> list[str]:
        """Main model first, then fallbacks, for OpenRouter's `models` routing."""
        main = self.assistant_model.strip() or DEFAULT_ASSISTANT_MODEL
        extra = [m.strip() for m in self.assistant_fallback_models.split(",") if m.strip()]
        return [main, *[m for m in extra if m != main]]

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env == "production"

    @model_validator(mode="after")
    def check_production_settings(self):
        if self.cookie_samesite == "none" and not self.secure_cookies:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        if self.app_env != "production":
            return self

        problems = []
        if self.secret_key == DEV_SECRET_KEY:
            problems.append(
                "SECRET_KEY must be set (generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
            )
        elif len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be at least 32 characters")
        if self.database_url == DEV_DATABASE_URL:
            problems.append("DATABASE_URL must be set")
        if not self.secure_cookies:
            problems.append("COOKIE_SECURE cannot be false")
        if "*" in self.origins:
            problems.append("ALLOWED_ORIGINS cannot contain '*'; list the frontend origin(s)")
        if not self.origins:
            problems.append("ALLOWED_ORIGINS must list the frontend origin(s)")
        if problems:
            raise ValueError("Invalid production configuration:\n  - " + "\n  - ".join(problems))
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
