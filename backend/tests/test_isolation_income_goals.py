"""User B can't read, change, delete or reference user A's income, income
categories, goals, contributions or recurring income."""

import csv
import io
from datetime import date

import pytest

API = "/api/v1"
NIL = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/income-categories"),
        ("post", "/income-categories"),
        ("get", "/incomes"),
        ("post", "/incomes"),
        ("get", "/goals"),
        ("post", "/goals"),
        ("get", f"/goals/{NIL}/contributions"),
        ("post", f"/recurring/{NIL}/mark-paid"),
        ("get", "/stats/cashflow"),
    ],
)
def test_new_endpoints_require_auth(client, method, path):
    assert getattr(client, method)(f"{API}{path}").status_code == 401


@pytest.fixture
def alice(client, auth_headers):
    today = date.today()
    cat = client.post(f"{API}/income-categories", json={"name": "Alice Tuition"}, headers=auth_headers).json()
    income = client.post(
        f"{API}/incomes",
        json={"amount": 7777, "income_category_id": cat["id"], "note": "alice secret income"},
        headers=auth_headers,
    ).json()
    goal = client.post(f"{API}/goals", json={"name": "Alice Goal", "target_amount": 1000}, headers=auth_headers).json()
    client.post(f"{API}/goals/{goal['id']}/contributions", json={"amount": 300}, headers=auth_headers)
    contribution = client.get(f"{API}/goals/{goal['id']}/contributions", headers=auth_headers).json()["contributions"][
        0
    ]
    rec = client.post(
        f"{API}/recurring",
        json={
            "kind": "income",
            "name": "Alice Salary",
            "amount": 5000,
            "income_category_id": cat["id"],
            "frequency": "monthly",
            "due_day": today.day,
        },
        headers=auth_headers,
    ).json()
    return {"cat": cat, "income": income, "goal": goal, "contribution": contribution, "rec": rec}


def test_lists_only_show_own_data(client, alice, other_headers):
    names = {
        c["name"] for c in client.get(f"{API}/income-categories", headers=other_headers).json()["income_categories"]
    }
    assert "Alice Tuition" not in names
    assert client.get(f"{API}/incomes", headers=other_headers).json()["incomes"] == []
    assert client.get(f"{API}/goals", headers=other_headers).json()["goals"] == []
    assert client.get(f"{API}/recurring?kind=income", headers=other_headers).json()["recurring_expenses"] == []
    assert client.get(f"{API}/stats/upcoming-recurring", headers=other_headers).json()["upcoming"] == []
    flow = client.get(f"{API}/stats/cashflow", headers=other_headers).json()
    assert (flow["income"], flow["allocated_to_goals"]) == (0, 0)
    text = client.get(f"{API}/export/csv?start_date=2020-01-01&end_date=2100-01-01", headers=other_headers).text
    assert "alice secret income" not in text
    assert list(csv.reader(io.StringIO(text)))[1:] == []


def test_cannot_touch_other_users_records(client, alice, auth_headers, other_headers):
    a = alice
    cat, inc, goal, contrib, rec = (
        a["cat"]["id"],
        a["income"]["id"],
        a["goal"]["id"],
        a["contribution"]["id"],
        a["rec"]["id"],
    )

    assert client.put(f"{API}/income-categories/{cat}", json={"name": "x"}, headers=other_headers).status_code == 404
    assert client.delete(f"{API}/income-categories/{cat}", headers=other_headers).status_code == 404
    assert client.put(f"{API}/incomes/{inc}", json={"amount": 1}, headers=other_headers).status_code == 404
    assert client.delete(f"{API}/incomes/{inc}", headers=other_headers).status_code == 404
    assert client.put(f"{API}/goals/{goal}", json={"name": "x"}, headers=other_headers).status_code == 404
    assert client.delete(f"{API}/goals/{goal}", headers=other_headers).status_code == 404
    assert client.get(f"{API}/goals/{goal}/contributions", headers=other_headers).status_code == 404
    assert (
        client.post(f"{API}/goals/{goal}/contributions", json={"amount": 1}, headers=other_headers).status_code == 404
    )
    assert client.delete(f"{API}/goals/{goal}/contributions/{contrib}", headers=other_headers).status_code == 404
    assert client.post(f"{API}/recurring/{rec}/mark-paid", headers=other_headers).status_code == 404

    # Alice's data is untouched, and B's mark-paid created nothing for anyone
    assert client.get(f"{API}/incomes", headers=auth_headers).json()["incomes"][0]["amount"] == 7777
    assert client.get(f"{API}/goals", headers=auth_headers).json()["goals"][0]["saved"] == 300
    assert client.get(f"{API}/incomes", headers=other_headers).json()["incomes"] == []


def test_cannot_use_other_users_income_category(client, alice, other_headers):
    cat = alice["cat"]["id"]
    assert (
        client.post(f"{API}/incomes", json={"amount": 1, "income_category_id": cat}, headers=other_headers).status_code
        == 400
    )
    assert (
        client.post(
            f"{API}/recurring",
            json={
                "kind": "income",
                "name": "x",
                "amount": 1,
                "income_category_id": cat,
                "frequency": "monthly",
                "due_day": 1,
            },
            headers=other_headers,
        ).status_code
        == 400
    )
    own_cat = client.get(f"{API}/income-categories", headers=other_headers).json()["income_categories"][0]["id"]
    own = client.post(f"{API}/incomes", json={"amount": 5, "income_category_id": own_cat}, headers=other_headers).json()
    assert (
        client.put(f"{API}/incomes/{own['id']}", json={"income_category_id": cat}, headers=other_headers).status_code
        == 400
    )


def test_names_unique_per_user_not_globally(client, alice, other_headers):
    assert (
        client.post(f"{API}/income-categories", json={"name": "Alice Tuition"}, headers=other_headers).status_code
        == 201
    )
    assert (
        client.post(f"{API}/goals", json={"name": "Alice Goal", "target_amount": 5}, headers=other_headers).status_code
        == 201
    )
