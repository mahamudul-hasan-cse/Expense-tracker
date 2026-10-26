"""Regression: "today" must be Asia/Dhaka's date, not the server's (usually UTC).

Bug found in Phase 4: date.today() on a UTC server is still "yesterday" between
00:00 and 06:00 in Dhaka, so an expense dated today (Dhaka) was rejected as a
future date, and due-today / current-month logic was a day behind.
"""
from datetime import date, datetime, timezone

import pytest

from app import timeutil
from tests.conftest import first_category_id

API = "/api/v1"

# 2030-03-10 20:30 UTC == 2030-03-11 02:30 in Dhaka (UTC+6). A date far from the
# real one, so the test fails on old code even on a machine set to Dhaka time.
UTC_EVENING = datetime(2030, 3, 10, 20, 30, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return UTC_EVENING.astimezone(tz) if tz else UTC_EVENING.replace(tzinfo=None)


@pytest.fixture
def dhaka_early_morning(monkeypatch):
    monkeypatch.setattr(timeutil, "datetime", _FrozenDatetime)


def test_today_uses_dhaka_date(dhaka_early_morning):
    assert timeutil.today() == date(2030, 3, 11)


def test_expense_dated_today_in_dhaka_is_accepted(client, auth_headers, dhaka_early_morning):
    cat = first_category_id(client, auth_headers)
    res = client.post(f"{API}/expenses", json={"amount": 80, "category_id": cat, "expense_date": "2030-03-11"}, headers=auth_headers)
    assert res.status_code == 201, res.text
    # Default date is Dhaka's today too
    res = client.post(f"{API}/expenses", json={"amount": 80, "category_id": cat}, headers=auth_headers)
    assert res.json()["expense_date"] == "2030-03-11"
    # The day after is still the future
    res = client.post(f"{API}/expenses", json={"amount": 80, "category_id": cat, "expense_date": "2030-03-12"}, headers=auth_headers)
    assert res.status_code == 422


def test_due_today_uses_dhaka_date(client, auth_headers, dhaka_early_morning):
    cat = first_category_id(client, auth_headers)
    rec = client.post(
        f"{API}/recurring",
        json={"name": "Rent", "amount": 100, "category_id": cat, "frequency": "monthly", "due_day": 11},
        headers=auth_headers,
    ).json()
    assert rec["next_due"] == "2030-03-11"
    upcoming = client.get(f"{API}/stats/upcoming-recurring", headers=auth_headers).json()["upcoming"]
    assert [(u["name"], u["days_until"]) for u in upcoming] == [("Rent", 0)]
