from datetime import date, timedelta

import pytest

from app.routers.recurring import calculate_next_due
from app.timeutil import today as app_today
from tests.conftest import first_category_id

API = "/api/v1"


# --- Due-date rules (pure function) ------------------------------------------


@pytest.mark.parametrize(
    "frequency, due_day, today, expected",
    [
        # weekly: 1=Monday … 7=Sunday; 2026-10-26 is a Monday
        ("weekly", 1, date(2026, 10, 26), date(2026, 10, 26)),  # due today
        ("weekly", 2, date(2026, 10, 26), date(2026, 10, 27)),
        ("weekly", 7, date(2026, 10, 26), date(2026, 11, 1)),
        ("weekly", 1, date(2026, 10, 27), date(2026, 11, 2)),  # just missed -> next week
        ("weekly", 5, date(2026, 12, 30), date(2027, 1, 1)),  # across New Year
        # monthly
        ("monthly", 5, date(2026, 10, 5), date(2026, 10, 5)),  # due today
        ("monthly", 5, date(2026, 10, 1), date(2026, 10, 5)),
        ("monthly", 5, date(2026, 10, 6), date(2026, 11, 5)),  # passed -> next month
        ("monthly", 31, date(2026, 2, 10), date(2026, 2, 28)),  # 31st in February (non-leap)
        ("monthly", 31, date(2028, 2, 10), date(2028, 2, 29)),  # leap year
        ("monthly", 31, date(2026, 4, 30), date(2026, 4, 30)),  # 30-day month, last day = due today
        ("monthly", 31, date(2026, 1, 31), date(2026, 1, 31)),
        ("monthly", 30, date(2026, 1, 31), date(2026, 2, 28)),  # passed in Jan -> clamped Feb
        ("monthly", 5, date(2026, 12, 6), date(2027, 1, 5)),  # December rollover
        ("monthly", 31, date(2026, 12, 31), date(2026, 12, 31)),
        ("monthly", 1, date(2026, 12, 2), date(2027, 1, 1)),
    ],
)
def test_calculate_next_due(frequency, due_day, today, expected):
    assert calculate_next_due(frequency, due_day, today) == expected


# --- API ---------------------------------------------------------------------


def _create(client, headers, **overrides):
    body = {
        "name": "Wifi",
        "amount": 800,
        "category_id": first_category_id(client, headers),
        "frequency": "monthly",
        "due_day": 5,
    }
    body.update(overrides)
    return client.post(f"{API}/recurring", json=body, headers=headers)


@pytest.mark.parametrize(
    "overrides",
    [
        {"frequency": "weekly", "due_day": 8},
        {"frequency": "monthly", "due_day": 32},
        {"due_day": 0},
        {"frequency": "yearly"},
        {"amount": 0},
        {"amount": 1.001},
        {"name": ""},
        {"name": "x" * 201},
    ],
)
def test_create_validation(client, auth_headers, overrides):
    assert _create(client, auth_headers, **overrides).status_code == 422


def test_create_and_list_with_next_due(client, auth_headers):
    today = app_today()
    rec = _create(client, auth_headers, due_day=today.day).json()
    assert rec["is_active"] is True
    assert rec["next_due"] == str(today)
    listed = client.get(f"{API}/recurring", headers=auth_headers).json()["recurring_expenses"]
    assert [r["id"] for r in listed] == [rec["id"]]


def test_update_rules(client, auth_headers):
    rec = _create(client, auth_headers, due_day=20).json()
    url = f"{API}/recurring/{rec['id']}"
    assert client.put(url, json={}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"name": None}, headers=auth_headers).status_code == 400
    # switching to weekly keeps due_day=20 -> invalid
    assert client.put(url, json={"frequency": "weekly"}, headers=auth_headers).status_code == 400
    weekly = client.put(url, json={"frequency": "weekly", "due_day": 3}, headers=auth_headers)
    assert weekly.status_code == 200 and weekly.json()["frequency"] == "weekly"
    assert (
        client.put(url, json={"category_id": "00000000-0000-0000-0000-000000000000"}, headers=auth_headers).status_code
        == 400
    )
    assert (
        client.put(
            f"{API}/recurring/00000000-0000-0000-0000-000000000000", json={"name": "x"}, headers=auth_headers
        ).status_code
        == 404
    )


def test_upcoming_window_and_paused_items(client, auth_headers):
    today = app_today()
    due_today = _create(client, auth_headers, name="Today", due_day=today.isoweekday(), frequency="weekly").json()
    in_three = _create(
        client, auth_headers, name="Soon", frequency="weekly", due_day=(today + timedelta(days=3)).isoweekday()
    ).json()
    paused = _create(client, auth_headers, name="Paused", frequency="weekly", due_day=today.isoweekday()).json()
    client.put(f"{API}/recurring/{paused['id']}", json={"is_active": False}, headers=auth_headers)

    upcoming = client.get(f"{API}/stats/upcoming-recurring", headers=auth_headers).json()["upcoming"]
    assert [(u["name"], u["days_until"]) for u in upcoming] == [("Today", 0), ("Soon", 3)]
    assert upcoming[0]["amount"] == 800 and upcoming[0]["category"]["name"]
    assert {due_today["id"], in_three["id"]} == {u["id"] for u in upcoming}


def test_delete(client, auth_headers):
    rec = _create(client, auth_headers).json()
    assert client.delete(f"{API}/recurring/{rec['id']}", headers=auth_headers).status_code == 204
    assert client.delete(f"{API}/recurring/{rec['id']}", headers=auth_headers).status_code == 404
