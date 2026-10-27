from datetime import date, timedelta

import pytest

from app.routers.recurring import next_unpaid_due
from app.timeutil import today as app_today

API = "/api/v1"


@pytest.fixture
def cats(client, auth_headers):
    inc = {
        c["name"]: c["id"]
        for c in client.get(f"{API}/income-categories", headers=auth_headers).json()["income_categories"]
    }
    exp = {c["name"]: c["id"] for c in client.get(f"{API}/categories", headers=auth_headers).json()["categories"]}
    return inc, exp


# --- next_unpaid_due (pure) --------------------------------------------------


@pytest.mark.parametrize(
    "frequency, due_day, last_paid, today, expected",
    [
        ("monthly", 5, None, date(2026, 10, 5), date(2026, 10, 5)),  # unpaid, due today
        ("monthly", 5, date(2026, 10, 5), date(2026, 10, 5), date(2026, 11, 5)),  # paid today -> next month
        ("monthly", 5, date(2026, 10, 5), date(2026, 10, 2), date(2026, 11, 5)),  # paid early
        ("monthly", 5, date(2026, 9, 5), date(2026, 10, 2), date(2026, 10, 5)),  # last month's payment
        ("monthly", 31, date(2026, 1, 31), date(2026, 1, 31), date(2026, 2, 28)),  # 31st -> Feb clamp
        ("monthly", 31, date(2028, 1, 31), date(2028, 1, 31), date(2028, 2, 29)),  # leap year
        ("monthly", 15, date(2026, 12, 15), date(2026, 12, 15), date(2027, 1, 15)),  # December rollover
        ("weekly", 1, date(2026, 10, 26), date(2026, 10, 26), date(2026, 11, 2)),  # Monday paid -> next Monday
        ("weekly", 7, date(2026, 12, 27), date(2026, 12, 27), date(2027, 1, 3)),  # across New Year
    ],
)
def test_next_unpaid_due(frequency, due_day, last_paid, today, expected):
    assert next_unpaid_due(frequency, due_day, last_paid, today) == expected


# --- Recurring income --------------------------------------------------------


def test_recurring_income_create_and_kind_rules(client, auth_headers, cats):
    inc, exp = cats
    base = {"name": "Salary", "amount": 50000, "frequency": "monthly", "due_day": 1}
    # kind must match the category field
    assert (
        client.post(
            f"{API}/recurring", json={**base, "kind": "income", "category_id": exp["Random"]}, headers=auth_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/recurring",
            json={**base, "kind": "expense", "income_category_id": inc["Salary"]},
            headers=auth_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/recurring",
            json={**base, "kind": "income", "income_category_id": inc["Salary"], "category_id": exp["Random"]},
            headers=auth_headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/recurring",
            json={**base, "kind": "income", "income_category_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_headers,
        ).status_code
        == 400
    )

    rec = client.post(
        f"{API}/recurring", json={**base, "kind": "income", "income_category_id": inc["Salary"]}, headers=auth_headers
    ).json()
    assert rec["kind"] == "income" and rec["category"] is None and rec["income_category"]["name"] == "Salary"
    # Existing clients that omit kind still create expenses
    bill = client.post(
        f"{API}/recurring", json={**base, "name": "Wifi", "category_id": exp["Wifi Bill"]}, headers=auth_headers
    ).json()
    assert bill["kind"] == "expense" and bill["category"]["name"] == "Wifi Bill" and bill["income_category"] is None

    assert (
        client.put(
            f"{API}/recurring/{rec['id']}", json={"category_id": exp["Random"]}, headers=auth_headers
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"{API}/recurring/{bill['id']}", json={"income_category_id": inc["Gift"]}, headers=auth_headers
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"{API}/recurring/{rec['id']}", json={"income_category_id": inc["Freelance"]}, headers=auth_headers
        ).json()["income_category"]["name"]
        == "Freelance"
    )

    kinds = client.get(f"{API}/recurring?kind=income", headers=auth_headers).json()["recurring_expenses"]
    assert [r["name"] for r in kinds] == ["Salary"]


def test_mark_paid_expense_creates_expense_and_advances_due(client, auth_headers, cats):
    _, exp = cats
    today = app_today()
    bill = client.post(
        f"{API}/recurring",
        json={
            "name": "Wifi",
            "amount": 800,
            "category_id": exp["Wifi Bill"],
            "frequency": "monthly",
            "due_day": today.day,
        },
        headers=auth_headers,
    ).json()
    assert bill["next_due"] == str(today)
    assert [
        u["name"] for u in client.get(f"{API}/stats/upcoming-recurring", headers=auth_headers).json()["upcoming"]
    ] == ["Wifi"]

    res = client.post(f"{API}/recurring/{bill['id']}/mark-paid", json={"amount": 850}, headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["record_type"] == "expense"
    assert body["recurring"]["last_paid_on"] == str(today)
    assert body["recurring"]["next_due"] > str(today)
    # The payment is a normal expense, with the bill's name as the note
    expenses = client.get(f"{API}/expenses", headers=auth_headers).json()["expenses"]
    assert [(e["amount"], e["note"], e["category"]["name"], e["expense_date"]) for e in expenses] == [
        (850, "Wifi", "Wifi Bill", str(today))
    ]
    # Paid items leave "Upcoming" until the next cycle
    assert client.get(f"{API}/stats/upcoming-recurring", headers=auth_headers).json()["upcoming"] == []


def test_mark_received_income_counts_in_cashflow(client, auth_headers, cats):
    inc, _ = cats
    today = app_today()
    salary = client.post(
        f"{API}/recurring",
        json={
            "kind": "income",
            "name": "Salary",
            "amount": 50000,
            "income_category_id": inc["Salary"],
            "frequency": "weekly",
            "due_day": today.isoweekday(),
        },
        headers=auth_headers,
    ).json()
    upcoming = client.get(f"{API}/stats/upcoming-recurring", headers=auth_headers).json()["upcoming"]
    assert [(u["name"], u["kind"], u["category"]["name"]) for u in upcoming] == [("Salary", "income", "Salary")]

    body = client.post(f"{API}/recurring/{salary['id']}/mark-paid", headers=auth_headers).json()
    assert body["record_type"] == "income"
    assert body["recurring"]["next_due"] == str(today + timedelta(days=7))
    incomes = client.get(f"{API}/incomes", headers=auth_headers).json()["incomes"]
    assert [(i["amount"], i["note"]) for i in incomes] == [(50000, "Salary")]
    flow = client.get(f"{API}/stats/cashflow", headers=auth_headers).json()
    assert flow["income"] == 50000


def test_mark_paid_rules(client, auth_headers, cats):
    _, exp = cats
    rec = client.post(
        f"{API}/recurring",
        json={"name": "Gym", "amount": 1500, "category_id": exp["Random"], "frequency": "monthly", "due_day": 1},
        headers=auth_headers,
    ).json()
    url = f"{API}/recurring/{rec['id']}/mark-paid"
    assert (
        client.post(url, json={"paid_on": str(app_today() + timedelta(days=1))}, headers=auth_headers).status_code
        == 422
    )
    assert client.post(url, json={"amount": 0}, headers=auth_headers).status_code == 422
    client.put(f"{API}/recurring/{rec['id']}", json={"is_active": False}, headers=auth_headers)
    assert client.post(url, headers=auth_headers).status_code == 400  # paused
    assert (
        client.post(f"{API}/recurring/00000000-0000-0000-0000-000000000000/mark-paid", headers=auth_headers).status_code
        == 404
    )


def test_changing_schedule_resets_paid_cycle(client, auth_headers, cats):
    _, exp = cats
    today = app_today()
    rec = client.post(
        f"{API}/recurring",
        json={
            "name": "Rent",
            "amount": 9000,
            "category_id": exp["Random"],
            "frequency": "monthly",
            "due_day": today.day,
        },
        headers=auth_headers,
    ).json()
    client.post(f"{API}/recurring/{rec['id']}/mark-paid", headers=auth_headers)
    moved = client.put(
        f"{API}/recurring/{rec['id']}",
        json={"frequency": "weekly", "due_day": today.isoweekday()},
        headers=auth_headers,
    ).json()
    assert moved["last_paid_on"] is None and moved["next_due"] == str(today)
