"""X-Client-IP is trusted only from the frontend proxy (with the shared secret)."""

import pytest
from pydantic import SecretStr

from app.client_ip import client_ip_from_scope
from app.config import Settings, get_settings

SECRET = "s" * 40


def scope(peer="10.0.0.5", **headers):
    return {
        "type": "http",
        "client": (peer, 443),
        "headers": [(k.replace("_", "-").encode(), v.encode()) for k, v in headers.items()],
    }


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "proxy_shared_secret", SecretStr(SECRET))


def test_proxy_with_the_secret_sets_the_client_ip(secret):
    assert client_ip_from_scope(scope(x_client_ip="203.0.113.7", x_proxy_secret=SECRET)) == "203.0.113.7"
    assert client_ip_from_scope(scope(x_client_ip="2001:db8::1", x_proxy_secret=SECRET)) == "2001:db8::1"


@pytest.mark.parametrize(
    "headers",
    [
        {"x_client_ip": "203.0.113.7"},  # no secret: a direct caller trying to pick its IP
        {"x_client_ip": "203.0.113.7", "x_proxy_secret": "wrong" * 8},
        {"x_client_ip": "not-an-ip", "x_proxy_secret": SECRET},
        {"x_client_ip": "203.0.113.7, 10.0.0.1", "x_proxy_secret": SECRET},
    ],
)
def test_anything_else_falls_back_to_the_peer(secret, headers):
    assert client_ip_from_scope(scope(**headers)) == "10.0.0.5"


def test_without_a_configured_secret_the_header_is_ignored(monkeypatch):
    monkeypatch.setattr(get_settings(), "proxy_shared_secret", SecretStr(""))
    assert client_ip_from_scope(scope(x_client_ip="203.0.113.7", x_proxy_secret="")) == "10.0.0.5"


def test_production_rejects_a_short_proxy_secret():
    with pytest.raises(ValueError, match="PROXY_SHARED_SECRET must be at least 32"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="k" * 48,
            database_url="postgresql://u:p@db.example.com/x",
            allowed_origins="https://app.example.com",
            proxy_shared_secret="short",
        )
