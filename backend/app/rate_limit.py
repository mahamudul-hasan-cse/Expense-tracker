from limits import parse_many
from slowapi import Limiter
from slowapi.middleware import _ASGIMiddlewareResponder
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.client_ip import client_ip
from app.config import get_settings

_settings = get_settings()

# Keyed by client IP: X-Client-IP from the frontend proxy when it proves itself with
# PROXY_SHARED_SECRET, otherwise the direct peer (see app/client_ip.py).
limiter = Limiter(
    key_func=client_ip,
    default_limits=[_settings.rate_limit_default],
    storage_uri=_settings.rate_limit_storage_uri,
    enabled=_settings.rate_limit_enabled,
)

_failed_login_limits = parse_many(_settings.rate_limit_login_failures)


class _StreamSafeResponder(_ASGIMiddlewareResponder):
    """slowapi's responder holds back http.response.start so it can edit headers, but
    re-sends it before EVERY body message. Streaming responses (SSE chat, CSV export)
    send several body messages, so uvicorn saw a second start and crashed the request
    ("Expected ASGI message 'http.response.body'"). This sends the start exactly once.
    """

    _start_sent = False

    async def send_wrapper(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            self.initial_message = message
            return
        if message["type"] == "http.response.body" and not self._start_sent:
            if self.error_response:
                self.initial_message["status"] = self.error_response.status_code
            if self.inject_headers:
                headers = MutableHeaders(raw=self.initial_message["headers"])
                self.limiter._inject_asgi_headers(headers, self.request.state.view_rate_limit)
            await self.send(self.initial_message)
            self._start_sent = True
        await self.send(message)


class RateLimitMiddleware:
    """Drop-in replacement for slowapi.middleware.SlowAPIASGIMiddleware (stream-safe)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        await _StreamSafeResponder(self.app)(scope, receive, send)


def login_attempts_allowed(email: str) -> bool:
    """False once an account has too many recent failed logins (any IP)."""
    if not limiter.enabled:
        return True
    return all(limiter.limiter.test(item, "login-failures", email) for item in _failed_login_limits)


def record_failed_login(email: str) -> None:
    if limiter.enabled:
        for item in _failed_login_limits:
            limiter.limiter.hit(item, "login-failures", email)
