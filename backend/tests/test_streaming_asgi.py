"""Regression: streaming responses must send http.response.start exactly once.

slowapi's ASGI middleware re-sent the start message before every body chunk. Real
uvicorn rejects that ("Expected ASGI message 'http.response.body'"), which broke the
assistant's SSE stream and made every CSV export log a crash. TestClient tolerates
the duplicate, so this drives the ASGI app directly with a strict `send`.
"""

import asyncio

import pytest

from app.main import app
from app.rate_limit import limiter
from app.timeutil import today as app_today
from tests.conftest import first_category_id

API = "/api/v1"


def strict_asgi_get(path: str, query: str, token: str) -> list[dict]:
    messages: list[dict] = []
    requested = False
    finished = asyncio.Event()

    async def receive():
        # Like a real server: the request body once, then wait and report a disconnect
        # after the response is complete (StreamingResponse listens for it)
        nonlocal requested
        if not requested:
            requested = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await finished.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start" and any(m["type"] == "http.response.start" for m in messages):
            finished.set()
            raise AssertionError("http.response.start sent twice")
        messages.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            finished.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": query.encode(),
        "headers": [(b"authorization", f"Bearer {token}".encode()), (b"host", b"test")],
        "client": ("127.0.0.1", 50000),
        "server": ("test", 80),
    }

    async def run():
        await asyncio.wait_for(app(scope, receive, send), timeout=30)

    asyncio.run(run())
    return messages


@pytest.fixture
def rate_limits_on():
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_csv_export_streams_with_rate_limiting_enabled(client, auth_headers, rate_limits_on):
    cat = first_category_id(client, auth_headers)
    for amount in (10, 20, 30):
        client.post(f"{API}/expenses", json={"amount": amount, "category_id": cat}, headers=auth_headers)
    token = auth_headers["Authorization"].split()[1]
    today = app_today()

    messages = strict_asgi_get(f"{API}/export/csv", f"start_date={today}&end_date={today}", token)
    starts = [m for m in messages if m["type"] == "http.response.start"]
    bodies = [m for m in messages if m["type"] == "http.response.body"]
    assert len(starts) == 1 and starts[0]["status"] == 200
    assert len(bodies) >= 2  # really a multi-chunk stream
    assert b"Date,Amount,Category,Note,Type" in b"".join(m.get("body", b"") for m in bodies)
    # Rate-limit headers are still injected into the single start message
    header_names = {k.lower() for k, _ in starts[0]["headers"]}
    assert b"x-request-id" in header_names
