"""Error monitoring with Sentry: only active when SENTRY_DSN is set.

Privacy: no request bodies, cookies, auth headers, query strings or IP addresses
are sent, and nothing from the AI assistant's messages. Errors carry the stack
trace, the route and the request id (the X-Request-ID also found in the logs).
"""

import logging
from typing import Any, Optional

from app.config import Settings

logger = logging.getLogger("app.monitoring")

# Headers that must never leave the server
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-proxy-secret", "x-api-key"}
# Log-record extras that identify a person
_SENSITIVE_EXTRAS = {"client_ip", "email", "user_email"}

_enabled = False


def scrub_event(event: dict[str, Any], hint: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """before_send hook: drop anything that could hold personal or secret data."""
    # The per-request access log line ("GET /x 500") duplicates the real exception event
    if event.get("logger") == "app.requests":
        return None
    extra = event.get("extra")
    if isinstance(extra, dict):
        for key in _SENSITIVE_EXTRAS:
            extra.pop(key, None)
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)  # bodies: expenses, notes, chat messages, passwords
        request.pop("cookies", None)
        request.pop("query_string", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {k: v for k, v in headers.items() if k.lower() not in _SENSITIVE_HEADERS}
        env = request.get("env")
        if isinstance(env, dict):
            env.pop("REMOTE_ADDR", None)
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}
    return event


def tag_request(request_id: str) -> None:
    """Attach the request id to any error reported while handling this request."""
    if _enabled:
        import sentry_sdk

        sentry_sdk.set_tag("request_id", request_id)


def init_sentry(settings: Settings) -> bool:
    """Start Sentry if a DSN is configured. Returns whether it was started."""
    global _enabled
    dsn = settings.sentry_dsn.get_secret_value()
    if not dsn:
        return False
    import sentry_sdk  # imported only when used

    _enabled = True

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment or settings.app_env,
        release=settings.sentry_release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        before_send=scrub_event,  # type: ignore[arg-type]
        # Our own logger.error/exception calls become events; info logs become breadcrumbs
        max_breadcrumbs=50,
    )
    logger.info("Sentry enabled", extra={"environment": settings.sentry_environment or settings.app_env})
    return True
