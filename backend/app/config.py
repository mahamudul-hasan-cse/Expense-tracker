from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache

# Only usable outside production; production must set SECRET_KEY explicitly
DEV_SECRET_KEY = "dev-insecure-secret-key-change-me-in-production"


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent"
    cors_origins: str = "http://localhost:3000"

    # Auth
    secret_key: str = DEV_SECRET_KEY
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Refresh cookie flags. Cross-site deployments (frontend and API on different
    # domains) need cookie_secure=true and cookie_samesite="none".
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def check_production_secrets(self):
        if self.app_env == "production" and self.secret_key == DEV_SECRET_KEY:
            raise ValueError("SECRET_KEY must be set to a strong random value when APP_ENV=production")
        if len(self.secret_key) < 32 and self.app_env == "production":
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
