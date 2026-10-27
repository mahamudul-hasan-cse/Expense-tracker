"""Sentry is off without a DSN, and never receives personal or secret data."""

import sentry_sdk

from app import monitoring
from app.config import Settings


def test_sentry_is_off_without_a_dsn():
    assert monitoring.init_sentry(Settings(_env_file=None, sentry_dsn="")) is False


def test_sentry_starts_with_privacy_options(monkeypatch):
    seen = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: seen.update(kw))
    monkeypatch.setattr(monitoring, "_enabled", False)
    settings = Settings(
        _env_file=None,
        sentry_dsn="https://public@o0.ingest.sentry.io/0",
        app_env="development",
        sentry_release="abc123",
    )
    assert monitoring.init_sentry(settings) is True
    assert seen["send_default_pii"] is False
    assert seen["before_send"] is monitoring.scrub_event
    assert (seen["environment"], seen["release"], seen["traces_sample_rate"]) == ("development", "abc123", 0.0)


def test_scrub_removes_bodies_secrets_and_personal_data():
    event = {
        "logger": "app",
        "extra": {"client_ip": "203.0.113.7", "status": 500},
        "user": {"id": "u1", "email": "alice@example.com", "ip_address": "203.0.113.7"},
        "request": {
            "url": "https://api.example.com/api/v1/expenses",
            "data": {"note": "private", "password": "hunter2"},
            "cookies": {"refresh_token": "secret"},
            "query_string": "search=salary",
            "headers": {"Authorization": "Bearer abc", "Cookie": "x", "User-Agent": "test"},
            "env": {"REMOTE_ADDR": "203.0.113.7"},
        },
    }
    scrubbed = monitoring.scrub_event(event)
    assert scrubbed is not None
    request = scrubbed["request"]
    assert "data" not in request and "cookies" not in request and "query_string" not in request
    assert request["headers"] == {"User-Agent": "test"}
    assert request["env"] == {}
    assert scrubbed["user"] == {"id": "u1"}
    assert scrubbed["extra"] == {"status": 500}


def test_access_log_lines_are_not_sent_twice():
    """The "GET /x 500" log line duplicates the exception event that Sentry already has."""
    assert monitoring.scrub_event({"logger": "app.requests", "message": "GET /x 500"}) is None
