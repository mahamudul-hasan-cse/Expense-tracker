"""The real client IP behind the frontend proxy, for rate limits and logs.

Browsers reach the API through the Next.js app (Vercel), so the backend's direct
peer is a Vercel server, and every user would share one rate-limit bucket. The
proxy (frontend/src/middleware.ts) therefore sends:

  X-Client-IP:     the visitor's IP, as Vercel saw it
  X-Proxy-Secret:  PROXY_SHARED_SECRET, known only to the proxy and this backend

X-Client-IP is trusted only with the right secret (constant-time compare), so a
client calling the API directly can't pick its own IP. Without a configured
secret, or with a wrong one, the direct peer address is used.
"""

import hmac
import ipaddress
from typing import Optional

from starlette.requests import Request
from starlette.types import Scope

from app.config import get_settings


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def client_ip_from_scope(scope: Scope) -> Optional[str]:
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    secret = get_settings().proxy_shared_secret.get_secret_value()
    if secret:
        sent = headers.get("x-proxy-secret", "")
        claimed = headers.get("x-client-ip", "").strip()
        if sent and hmac.compare_digest(sent.encode(), secret.encode()) and _valid_ip(claimed):
            return claimed
    client = scope.get("client")
    return client[0] if client else None


def client_ip(request: Request) -> str:
    """slowapi key function: the client IP (see module docstring)."""
    return client_ip_from_scope(request.scope) or "127.0.0.1"
