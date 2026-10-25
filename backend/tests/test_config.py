import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings

STRONG_KEY = "x" * 48
PROD = {
    "app_env": "production",
    "secret_key": STRONG_KEY,
    "database_url": "postgresql://u:p@db.example.com/wallet",
    "allowed_origins": "https://app.example.com",
    "_env_file": None,
}


def test_development_defaults_allow_plain_http_cookies():
    s = Settings(app_env="development", _env_file=None)
    assert s.secure_cookies is False
    assert s.cookie_samesite == "strict"


def test_valid_production_config():
    s = Settings(**PROD)
    assert s.secure_cookies is True
    assert s.origins == ["https://app.example.com"]


def test_origins_parsing_and_legacy_env_name(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert Settings(_env_file=None).origins == ["https://a.example.com", "https://b.example.com"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": DEV_SECRET_KEY},
        {"secret_key": "too-short"},
        {"cookie_secure": False},
        {"allowed_origins": "*"},
        {"allowed_origins": " "},
        {"database_url": "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent"},
    ],
)
def test_production_rejects_insecure_settings(overrides):
    with pytest.raises(ValidationError):
        Settings(**{**PROD, **overrides})


def test_samesite_none_requires_secure():
    with pytest.raises(ValidationError):
        Settings(app_env="development", cookie_samesite="none", _env_file=None)
    assert Settings(app_env="development", cookie_samesite="none", cookie_secure=True, _env_file=None)


def test_refresh_cookie_flags(client):
    res = client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": "longenough"})
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "path=/api/v1/auth" in cookie
    assert "samesite=strict" in cookie
