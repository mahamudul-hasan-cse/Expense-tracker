"""User A must never be able to read, edit or delete user B's data."""

import pytest

from app.timeutil import today as app_today
from tests.conftest import first_category_id

API = "/api/v1"


@pytest.fixture
def alice_data(client, auth_headers):
    """Create one of everything for Alice."""
    today = app_today()
    category = client.post(f"{API}/categories", json={"name": "Alice Only", "icon": "A"}, headers=auth_headers).json()
    expense = client.post(
        f"{API}/expenses",
        json={"amount": 123.45, "category_id": category["id"], "note": "alice secret"},
        headers=auth_headers,
    ).json()
    recurring = client.post(
        f"{API}/recurring",
        json={
            "name": "Alice Rent",
            "amount": 500,
            "category_id": category["id"],
            "frequency": "monthly",
            "due_day": today.day,
        },
        headers=auth_headers,
    ).json()
    budget = client.post(
        f"{API}/budgets",
        json={"category_id": category["id"], "amount": 1000, "month": today.month, "year": today.year},
        headers=auth_headers,
    ).json()
    return {"category": category, "expense": expense, "recurring": recurring, "budget": budget}


@pytest.mark.parametrize(
    "path",
    [
        "/categories",
        "/expenses",
        "/recurring",
        "/budgets",
        "/budgets/summary",
        "/stats/summary",
        "/stats/upcoming-recurring",
        "/export/csv?start_date=2020-01-01&end_date=2100-01-01",
    ],
)
def test_every_data_endpoint_requires_auth(client, path):
    assert client.get(f"{API}{path}").status_code == 401


def test_lists_only_show_own_data(client, alice_data, other_headers):
    cats = client.get(f"{API}/categories", headers=other_headers).json()["categories"]
    assert "Alice Only" not in {c["name"] for c in cats}
    assert client.get(f"{API}/expenses", headers=other_headers).json()["expenses"] == []
    assert client.get(f"{API}/recurring", headers=other_headers).json()["recurring_expenses"] == []
    assert client.get(f"{API}/budgets", headers=other_headers).json()["budgets"] == []
    assert client.get(f"{API}/stats/summary", headers=other_headers).json()["total_spent"] == 0
    assert client.get(f"{API}/stats/upcoming-recurring", headers=other_headers).json()["upcoming"] == []
    csv = client.get(f"{API}/export/csv?start_date=2020-01-01&end_date=2100-01-01", headers=other_headers).text
    assert "alice secret" not in csv


def test_cannot_edit_or_delete_other_users_records(client, alice_data, auth_headers, other_headers):
    ids = {k: v["id"] for k, v in alice_data.items()}

    assert (
        client.put(f"{API}/categories/{ids['category']}", json={"name": "Hacked"}, headers=other_headers).status_code
        == 404
    )
    assert client.delete(f"{API}/categories/{ids['category']}", headers=other_headers).status_code == 404
    assert client.put(f"{API}/expenses/{ids['expense']}", json={"amount": 1}, headers=other_headers).status_code == 404
    assert client.delete(f"{API}/expenses/{ids['expense']}", headers=other_headers).status_code == 404
    assert (
        client.put(f"{API}/recurring/{ids['recurring']}", json={"is_active": False}, headers=other_headers).status_code
        == 404
    )
    assert client.delete(f"{API}/recurring/{ids['recurring']}", headers=other_headers).status_code == 404
    assert client.put(f"{API}/budgets/{ids['budget']}", json={"amount": 1}, headers=other_headers).status_code == 404
    assert client.delete(f"{API}/budgets/{ids['budget']}", headers=other_headers).status_code == 404

    # Alice's data is untouched
    expense = client.get(f"{API}/expenses", headers=auth_headers).json()["expenses"][0]
    assert expense["amount"] == 123.45
    assert client.get(f"{API}/recurring", headers=auth_headers).json()["recurring_expenses"][0]["is_active"] is True
    assert client.get(f"{API}/budgets", headers=auth_headers).json()["budgets"][0]["amount"] == 1000


def test_cannot_use_other_users_category(client, alice_data, other_headers):
    alice_category = alice_data["category"]["id"]
    today = app_today()
    assert (
        client.post(
            f"{API}/expenses", json={"amount": 10, "category_id": alice_category}, headers=other_headers
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"{API}/recurring",
            json={"name": "x", "amount": 10, "category_id": alice_category, "frequency": "monthly", "due_day": 1},
            headers=other_headers,
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"{API}/budgets",
            json={"category_id": alice_category, "amount": 10, "month": today.month, "year": today.year},
            headers=other_headers,
        ).status_code
        == 400
    )

    # Moving one's own expense into someone else's category is also refused
    own = client.post(
        f"{API}/expenses",
        json={"amount": 5, "category_id": first_category_id(client, other_headers)},
        headers=other_headers,
    ).json()
    assert (
        client.put(
            f"{API}/expenses/{own['id']}", json={"category_id": alice_category}, headers=other_headers
        ).status_code
        == 400
    )


def test_category_names_are_unique_per_user_not_globally(client, alice_data, auth_headers, other_headers):
    assert client.post(f"{API}/categories", json={"name": "alice only"}, headers=auth_headers).status_code == 400
    assert client.post(f"{API}/categories", json={"name": "Alice Only"}, headers=other_headers).status_code == 201
