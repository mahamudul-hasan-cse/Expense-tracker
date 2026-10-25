import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings

STRONG_KEY = "x" * 48


def test_development_defaults_allow_plain_http_cookies():
    s = Settings(app_env="development", _env_file=None)
    assert s.secure_cookies is False
    assert s.cookie_samesite == "strict"


def test_production_defaults_to_secure_cookies():
    s = Settings(app_env="production", secret_key=STRONG_KEY, _env_file=None)
    assert s.secure_cookies is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": DEV_SECRET_KEY},
        {"secret_key": "too-short"},
        {"secret_key": STRONG_KEY, "cookie_secure": False},
    ],
)
def test_production_rejects_insecure_settings(overrides):
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None, **overrides)


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
