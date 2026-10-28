"""Every API route needs a signed-in user, except a short, explicit public list.

Enumerates the app's routes, so a new endpoint that forgets authentication fails here.
"""

import re
import uuid

import pytest

from app.main import app

PUBLIC = {
    ("GET", "/"),
    ("GET", "/health"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),  # uses the refresh cookie; 401 without it
    ("POST", "/api/v1/auth/logout"),  # uses the refresh cookie; always succeeds (idempotent)
}

# From the OpenAPI schema: FastAPI keeps included routers nested, so app.routes doesn't
# list every endpoint directly
ROUTES = sorted(
    (method.upper(), path)
    for path, operations in app.openapi()["paths"].items()
    for method in operations
    if (method.upper(), path) not in PUBLIC
)


def test_the_route_list_is_complete():
    # 48 protected operations on 2026-10-28; a sudden drop means routes went missing
    assert len(ROUTES) >= 45


@pytest.mark.parametrize("method, path", ROUTES)
def test_route_rejects_requests_without_a_token(client, method, path):
    url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
    res = client.request(method, url, json={})
    assert res.status_code == 401, f"{method} {path} answered {res.status_code} without a token"
    assert res.json()["error"]["code"] == "unauthorized"


def test_responses_carry_security_headers(client):
    for res in (client.get("/health"), client.get("/api/v1/expenses")):
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("method, path", ROUTES)
def test_route_rejects_a_forged_token(client, method, path):
    url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
    forged = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyJ9.not-a-real-signature"
    res = client.request(method, url, json={}, headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401
