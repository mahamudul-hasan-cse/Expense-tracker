import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.logging_config import JsonFormatter
from app.main import app
from app.rate_limit import limiter

API = "/api/v1"


# --- /health -----------------------------------------------------------------


def test_health_checks_database(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "database": "ok"}


def test_health_reports_database_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("connection refused")

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        res = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db)
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "service_unavailable"


# --- Error format ------------------------------------------------------------


def _assert_error_shape(res, status, code):
    assert res.status_code == status
    body = res.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["request_id"] == res.headers["x-request-id"]


def test_error_format_401(client):
    _assert_error_shape(client.get(f"{API}/expenses"), 401, "unauthorized")


def test_error_format_404(client, auth_headers):
    res = client.delete(f"{API}/expenses/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    _assert_error_shape(res, 404, "not_found")
    assert res.json()["error"]["message"] == "Expense not found"


def test_error_format_400(client, auth_headers):
    res = client.put(f"{API}/expenses/00000000-0000-0000-0000-000000000000", json={}, headers=auth_headers)
    # Unknown id is checked before the empty body
    _assert_error_shape(res, 404, "not_found")


def test_error_format_422_lists_fields(client, auth_headers):
    res = client.post(f"{API}/expenses", json={"amount": 1.234, "category_id": "nope"}, headers=auth_headers)
    _assert_error_shape(res, 422, "validation_error")
    fields = {d["field"] for d in res.json()["error"]["details"]}
    assert fields == {"amount", "category_id"}


def test_unknown_route_uses_error_format(client):
    _assert_error_shape(client.get(f"{API}/does-not-exist"), 404, "not_found")


def test_unhandled_errors_hide_internals():
    @app.get("/_test/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/_test/boom")
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/_test/boom"]
    assert res.status_code == 500
    body = res.json()
    assert body["error"]["code"] == "internal_error"
    assert "secret" not in res.text
    assert "Traceback" not in res.text


def test_request_id_is_propagated(client):
    res = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert res.headers["x-request-id"] == "abc-123"


# --- Rate limiting -----------------------------------------------------------


@pytest.fixture
def rate_limits_on():
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_login_is_rate_limited(client, rate_limits_on):
    payload = {"email": "nobody@example.com", "password": "wrong-password"}
    statuses = [client.post(f"{API}/auth/login", json=payload).status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    res = client.post(f"{API}/auth/login", json=payload)
    _assert_error_shape(res, 429, "rate_limited")


def test_failed_logins_are_limited_per_account(client, rate_limits_on, monkeypatch):
    from app.config import get_settings
    from tests.conftest import register

    # Lift the per-IP limit so only the per-account limit can trigger, as if
    # each attempt came from a different (or spoofed) IP
    monkeypatch.setattr(get_settings(), "rate_limit_auth", "1000/minute")
    register(client, "target@example.com", "the-real-password")
    payload = {"email": "TARGET@example.com", "password": "guess"}
    statuses = [client.post(f"{API}/auth/login", json=payload).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    # Even the right password is refused while the account is locked
    ok = client.post(f"{API}/auth/login", json={"email": "target@example.com", "password": "the-real-password"})
    assert ok.status_code == 429
    # Other accounts are unaffected
    register(client, "other@example.com", "other-password")
    assert (
        client.post(f"{API}/auth/login", json={"email": "other@example.com", "password": "other-password"}).status_code
        == 200
    )


def test_health_is_not_rate_limited(client, rate_limits_on):
    assert all(client.get("/health").status_code == 200 for _ in range(10))


# --- CORS --------------------------------------------------------------------


def _preflight(client, origin):
    return client.options(
        f"{API}/expenses",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_cors_allows_configured_origin(client):
    res = _preflight(client, "http://localhost:3000")
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert res.headers["access-control-allow-credentials"] == "true"


def test_cors_rejects_other_origins(client):
    res = _preflight(client, "https://evil.example.com")
    assert "access-control-allow-origin" not in res.headers


# --- Pagination --------------------------------------------------------------


def test_categories_are_paginated(client, auth_headers):
    body = client.get(f"{API}/categories?page=2&limit=3", headers=auth_headers).json()
    assert len(body["categories"]) == 1
    assert body["pagination"] == {"page": 2, "limit": 3, "total_items": 4, "total_pages": 2}


def test_recurring_and_budgets_include_pagination(client, auth_headers):
    assert client.get(f"{API}/recurring", headers=auth_headers).json()["pagination"]["total_items"] == 0
    assert client.get(f"{API}/budgets", headers=auth_headers).json()["pagination"]["total_items"] == 0


# --- Logging -----------------------------------------------------------------


def test_json_log_format():
    record = logging.makeLogRecord(
        {"name": "app.test", "levelname": "INFO", "msg": "hello %s", "args": ("world",), "status": 200}
    )
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "hello world"
    assert entry["level"] == "INFO"
    assert entry["status"] == 200
