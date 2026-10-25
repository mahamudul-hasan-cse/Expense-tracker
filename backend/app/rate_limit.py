from limits import parse_many
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()

# Keyed by client IP (request.client). Behind a proxy that is only the real
# client when uvicorn runs with --proxy-headers and FORWARDED_ALLOW_IPS lists the
# proxy, and something in front appends the client IP to X-Forwarded-For (a
# self-hosted `next start` passes the header through but doesn't add to it).
# See docs/PRODUCTION_PLAN.md, "Client IPs behind the proxy".
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.rate_limit_default],
    storage_uri=_settings.rate_limit_storage_uri,
    enabled=_settings.rate_limit_enabled,
)

_failed_login_limits = parse_many(_settings.rate_limit_login_failures)


def login_attempts_allowed(email: str) -> bool:
    """False once an account has too many recent failed logins (any IP)."""
    if not limiter.enabled:
        return True
    return all(limiter.limiter.test(item, "login-failures", email) for item in _failed_login_limits)


def record_failed_login(email: str) -> None:
    if limiter.enabled:
        for item in _failed_login_limits:
            limiter.limiter.hit(item, "login-failures", email)
