from datetime import date, timedelta

import pytest

from tests.conftest import first_category_id

API = "/api/v1"


def add(client, headers, amount, category_id, note=None, expense_date=None):
    body = {"amount": amount, "category_id": category_id}
    if note is not None:
        body["note"] = note
    if expense_date is not None:
        body["expense_date"] = str(expense_date)
    res = client.post(f"{API}/expenses", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# --- Money validation --------------------------------------------------------


@pytest.mark.parametrize(
    "amount, status",
    [
        (0.01, 201),
        (350, 201),
        (99_999_999.99, 201),
        (0, 422),
        (-5, 422),
        (1.234, 422),  # more than 2 decimals
        (100_000_000, 422),  # above the max
        ("abc", 422),
    ],
)
def test_amount_validation(client, auth_headers, amount, status):
    cat = first_category_id(client, auth_headers)
    res = client.post(f"{API}/expenses", json={"amount": amount, "category_id": cat}, headers=auth_headers)
    assert res.status_code == status, res.text


def test_amount_is_returned_as_number_with_2dp_precision(client, auth_headers):
    cat = first_category_id(client, auth_headers)
    exp = add(client, auth_headers, "1234.50", cat)
    assert exp["amount"] == 1234.5


def test_future_date_rejected_today_default(client, auth_headers):
    cat = first_category_id(client, auth_headers)
    tomorrow = date.today() + timedelta(days=1)
    res = client.post(
        f"{API}/expenses", json={"amount": 1, "category_id": cat, "expense_date": str(tomorrow)}, headers=auth_headers
    )
    assert res.status_code == 422
    assert "future" in res.json()["error"]["message"]
    assert add(client, auth_headers, 1, cat)["expense_date"] == str(date.today())


def test_note_max_length(client, auth_headers):
    cat = first_category_id(client, auth_headers)
    assert (
        client.post(
            f"{API}/expenses", json={"amount": 1, "category_id": cat, "note": "x" * 501}, headers=auth_headers
        ).status_code
        == 422
    )
    add(client, auth_headers, 1, cat, note="x" * 500)


def test_unknown_category_rejected(client, auth_headers):
    res = client.post(
        f"{API}/expenses",
        json={"amount": 1, "category_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers,
    )
    assert res.status_code == 400


# --- Update / delete ---------------------------------------------------------


def test_update_rules(client, auth_headers):
    cat = first_category_id(client, auth_headers)
    exp = add(client, auth_headers, 10, cat, note="old")
    url = f"{API}/expenses/{exp['id']}"

    assert client.put(url, json={}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"amount": None}, headers=auth_headers).status_code == 400
    assert (
        client.put(url, json={"expense_date": str(date.today() + timedelta(days=1))}, headers=auth_headers).status_code
        == 422
    )
    cleared = client.put(url, json={"note": None}, headers=auth_headers)
    assert cleared.status_code == 200 and cleared.json()["note"] is None
    assert client.put(url, json={"amount": 99.99}, headers=auth_headers).json()["amount"] == 99.99


def test_delete_then_404(client, auth_headers):
    cat = first_category_id(client, auth_headers)
    exp = add(client, auth_headers, 10, cat)
    assert client.delete(f"{API}/expenses/{exp['id']}", headers=auth_headers).status_code == 204
    assert client.delete(f"{API}/expenses/{exp['id']}", headers=auth_headers).status_code == 404
    assert client.put(f"{API}/expenses/{exp['id']}", json={"amount": 1}, headers=auth_headers).status_code == 404


# --- Listing: filters, search, sort, pagination ------------------------------


@pytest.fixture
def seeded(client, auth_headers):
    cats = {c["name"]: c["id"] for c in client.get(f"{API}/categories", headers=auth_headers).json()["categories"]}
    today = date.today()
    add(client, auth_headers, 30, cats["Rickshaw"], "campus", today)
    add(client, auth_headers, 800, cats["Wifi Bill"], "monthly wifi", today - timedelta(days=3))
    add(client, auth_headers, 250, cats["Random"], "lunch 100% spicy", today - timedelta(days=10))
    add(client, auth_headers, 60, cats["Rickshaw"], "home_trip", today - timedelta(days=40))
    return cats, today


def _list(client, headers, **params):
    res = client.get(f"{API}/expenses", params=params, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_filters(client, auth_headers, seeded):
    cats, today = seeded
    assert {e["note"] for e in _list(client, auth_headers, category_id=cats["Rickshaw"])["expenses"]} == {
        "campus",
        "home_trip",
    }
    in_range = _list(
        client, auth_headers, start_date=str(today - timedelta(days=10)), end_date=str(today - timedelta(days=3))
    )
    assert {e["note"] for e in in_range["expenses"]} == {"monthly wifi", "lunch 100% spicy"}


def test_search_is_case_insensitive_and_escapes_wildcards(client, auth_headers, seeded):
    assert [e["note"] for e in _list(client, auth_headers, search="WIFI")["expenses"]] == ["monthly wifi"]
    # "%" and "_" are literal, not LIKE wildcards
    assert [e["note"] for e in _list(client, auth_headers, search="100%")["expenses"]] == ["lunch 100% spicy"]
    assert [e["note"] for e in _list(client, auth_headers, search="_")["expenses"]] == ["home_trip"]


@pytest.mark.parametrize(
    "sort, expected",
    [
        ("date_desc", [30, 800, 250, 60]),
        ("date_asc", [60, 250, 800, 30]),
        ("amount_desc", [800, 250, 60, 30]),
        ("amount_asc", [30, 60, 250, 800]),
    ],
)
def test_sorting(client, auth_headers, seeded, sort, expected):
    assert [e["amount"] for e in _list(client, auth_headers, sort=sort)["expenses"]] == expected


def test_pagination(client, auth_headers, seeded):
    page1 = _list(client, auth_headers, limit=3, page=1)
    page2 = _list(client, auth_headers, limit=3, page=2)
    assert page1["pagination"] == {"page": 1, "limit": 3, "total_items": 4, "total_pages": 2}
    assert len(page1["expenses"]) == 3 and len(page2["expenses"]) == 1
    assert client.get(f"{API}/expenses?limit=101", headers=auth_headers).status_code == 422
    assert client.get(f"{API}/expenses?page=0", headers=auth_headers).status_code == 422
