from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.goals import compute_progress

API = "/api/v1"


@pytest.fixture
def ids(client, auth_headers):
    inc = {
        c["name"]: c["id"]
        for c in client.get(f"{API}/income-categories", headers=auth_headers).json()["income_categories"]
    }
    exp = {c["name"]: c["id"] for c in client.get(f"{API}/categories", headers=auth_headers).json()["categories"]}
    return inc, exp


def _income(client, h, amount, cid, when):
    assert (
        client.post(
            f"{API}/incomes", json={"amount": amount, "income_category_id": cid, "income_date": str(when)}, headers=h
        ).status_code
        == 201
    )


def _expense(client, h, amount, cid, when):
    assert (
        client.post(
            f"{API}/expenses", json={"amount": amount, "category_id": cid, "expense_date": str(when)}, headers=h
        ).status_code
        == 201
    )


def _cashflow(client, h, month):
    res = client.get(f"{API}/stats/cashflow?month={month}", headers=h)
    assert res.status_code == 200, res.text
    return res.json()


# --- Cashflow ----------------------------------------------------------------


def test_cashflow_positive_month(client, auth_headers, ids):
    inc, exp = ids
    _income(client, auth_headers, 40000, inc["Salary"], date(2026, 3, 1))
    _income(client, auth_headers, 10000, inc["Freelance"], date(2026, 3, 31))
    _income(client, auth_headers, 99999, inc["Salary"], date(2026, 2, 28))  # other month
    _expense(client, auth_headers, 12500, exp["Random"], date(2026, 3, 15))
    c = _cashflow(client, auth_headers, "2026-03")
    assert (c["start_date"], c["end_date"]) == ("2026-03-01", "2026-03-31")
    assert (c["income"], c["spent"], c["saved"], c["savings_rate"]) == (50000, 12500, 37500, 75.0)


def test_cashflow_negative_month_is_overspent(client, auth_headers, ids):
    inc, exp = ids
    _income(client, auth_headers, 1000, inc["Gift"], date(2026, 4, 2))
    _expense(client, auth_headers, 1500.5, exp["Random"], date(2026, 4, 3))
    c = _cashflow(client, auth_headers, "2026-04")
    assert c["saved"] == -500.5
    assert c["savings_rate"] == -50.0


def test_cashflow_without_income_has_null_rate(client, auth_headers, ids):
    _, exp = ids
    _expense(client, auth_headers, 200, exp["Random"], date(2026, 5, 3))
    c = _cashflow(client, auth_headers, "2026-05")
    assert (c["income"], c["spent"], c["saved"], c["savings_rate"]) == (0, 200, -200, None)
    empty = _cashflow(client, auth_headers, "2026-06")
    assert (empty["income"], empty["spent"], empty["saved"], empty["savings_rate"]) == (0, 0, 0, None)


def test_cashflow_month_validation_and_default(client, auth_headers):
    for bad in ("2026-13", "2026-3", "march", "2026-00"):
        assert client.get(f"{API}/stats/cashflow?month={bad}", headers=auth_headers).status_code == 422
    today = date.today()
    assert (
        client.get(f"{API}/stats/cashflow", headers=auth_headers).json()["month"]
        == f"{today.year:04d}-{today.month:02d}"
    )
    assert _cashflow(client, auth_headers, "2028-02")["end_date"] == "2028-02-29"  # leap year


def test_contributions_never_count_as_spending(client, auth_headers, ids):
    """Requirement: goal contributions are allocations of savings, not expenses."""
    inc, exp = ids
    today = date.today()
    _income(client, auth_headers, 10000, inc["Salary"], today)
    _expense(client, auth_headers, 2500, exp["Random"], today)
    client.post(
        f"{API}/budgets",
        json={"category_id": exp["Random"], "amount": 5000, "month": today.month, "year": today.year},
        headers=auth_headers,
    )
    month = f"{today.year:04d}-{today.month:02d}"
    before = (
        _cashflow(client, auth_headers, month),
        client.get(f"{API}/stats/summary", headers=auth_headers).json(),
        client.get(f"{API}/budgets/summary", headers=auth_headers).json(),
    )

    goal = client.post(f"{API}/goals", json={"name": "Laptop", "target_amount": 80000}, headers=auth_headers).json()
    assert (
        client.post(f"{API}/goals/{goal['id']}/contributions", json={"amount": 4000}, headers=auth_headers).status_code
        == 201
    )

    after_flow = _cashflow(client, auth_headers, month)
    assert (after_flow["income"], after_flow["spent"], after_flow["saved"]) == (10000, 2500, 7500)
    assert after_flow["allocated_to_goals"] == 4000 and after_flow["unallocated"] == 3500
    assert (
        client.get(f"{API}/stats/summary", headers=auth_headers).json()["total_spent"]
        == before[1]["total_spent"]
        == 2500
    )
    assert (
        client.get(f"{API}/budgets/summary", headers=auth_headers).json()["total_spent"]
        == before[2]["total_spent"]
        == 2500
    )
    assert client.get(f"{API}/expenses", headers=auth_headers).json()["pagination"]["total_items"] == 1


# --- Goal progress (pure function, fixed "today") ----------------------------

TODAY = date(2026, 6, 1)


def _goal(target, target_date=None, created=date(2026, 1, 1)):
    return SimpleNamespace(
        target_amount=Decimal(target),
        target_date=target_date,
        created_at=datetime(created.year, created.month, created.day, 6, 0, tzinfo=timezone.utc),
    )


def test_completed_goal():
    p = compute_progress(_goal(1000, date(2026, 12, 31)), Decimal("1200"), TODAY)
    assert (p.state, p.remaining, p.required_per_month, p.on_track, p.progress_pct) == ("completed", 0, 0, True, 120.0)


def test_completed_goal_without_deadline_or_past_deadline():
    assert compute_progress(_goal(500), Decimal("500"), TODAY).state == "completed"
    assert compute_progress(_goal(500, date(2026, 2, 1)), Decimal("500"), TODAY).state == "completed"


def test_no_deadline():
    p = compute_progress(_goal(1000), Decimal("250"), TODAY)
    assert (p.state, p.remaining, p.required_per_month, p.on_track, p.months_left) == (
        "no_deadline",
        750,
        None,
        None,
        None,
    )
    assert p.progress_pct == 25.0


def test_past_deadline_is_overdue_with_remaining_due_now():
    p = compute_progress(_goal(1000, date(2026, 5, 31)), Decimal("400"), TODAY)
    assert (p.state, p.on_track, p.months_left, p.required_per_month) == ("overdue", False, 0, Decimal("600"))


def test_deadline_today_is_not_overdue():
    p = compute_progress(_goal(1000, TODAY), Decimal("400"), TODAY)
    assert p.state in {"on_track", "behind"} and p.months_left == 1 and p.required_per_month == Decimal("600.00")


def test_on_track_vs_behind():
    # Created Jan 1, deadline Dec 31 (364 days); on Jun 1, 151 days elapsed -> expected ~41.5%
    goal = _goal(12000, date(2026, 12, 31))
    ahead = compute_progress(goal, Decimal("6000"), TODAY)
    behind = compute_progress(goal, Decimal("3000"), TODAY)
    assert (ahead.state, ahead.on_track) == ("on_track", True)
    assert (behind.state, behind.on_track) == ("behind", False)
    # 213 days left -> 7 months; (12000-3000)/7 = 1285.714... rounded up
    assert behind.months_left == 7 and behind.required_per_month == Decimal("1285.72")


def test_short_deadline_needs_at_least_one_month():
    p = compute_progress(_goal(1000, TODAY + timedelta(days=3)), Decimal("0"), TODAY)
    assert p.months_left == 1 and p.required_per_month == Decimal("1000.00")


# --- Goals API ---------------------------------------------------------------


def test_goal_crud_and_validation(client, auth_headers):
    future = str(date.today() + timedelta(days=200))
    assert client.post(f"{API}/goals", json={"name": "x", "target_amount": 0}, headers=auth_headers).status_code == 422
    assert (
        client.post(f"{API}/goals", json={"name": "  ", "target_amount": 10}, headers=auth_headers).status_code == 422
    )
    assert (
        client.post(
            f"{API}/goals",
            json={"name": "x", "target_amount": 10, "target_date": str(date.today())},
            headers=auth_headers,
        ).status_code
        == 422
    )

    goal = client.post(
        f"{API}/goals",
        json={"name": " Laptop ", "icon": "💻", "target_amount": 80000, "target_date": future},
        headers=auth_headers,
    )
    assert goal.status_code == 201
    g = goal.json()
    assert (g["name"], g["saved"], g["remaining"], g["status"], g["state"]) == (
        "Laptop",
        0,
        80000,
        "active",
        "on_track",
    )
    assert (
        client.post(f"{API}/goals", json={"name": "laptop", "target_amount": 1}, headers=auth_headers).status_code
        == 400
    )

    url = f"{API}/goals/{g['id']}"
    assert client.put(url, json={}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"name": None}, headers=auth_headers).status_code == 400
    no_deadline = client.put(url, json={"target_date": None}, headers=auth_headers).json()
    assert no_deadline["target_date"] is None and no_deadline["state"] == "no_deadline"
    archived = client.put(url, json={"status": "archived"}, headers=auth_headers).json()
    assert archived["status"] == "archived"
    assert [x["name"] for x in client.get(f"{API}/goals?status=active", headers=auth_headers).json()["goals"]] == []
    assert [x["name"] for x in client.get(f"{API}/goals?status=archived", headers=auth_headers).json()["goals"]] == [
        "Laptop"
    ]


def test_contributions_and_withdrawals(client, auth_headers):
    g = client.post(f"{API}/goals", json={"name": "Trip", "target_amount": 1000}, headers=auth_headers).json()
    url = f"{API}/goals/{g['id']}/contributions"
    assert client.post(url, json={"amount": 0}, headers=auth_headers).status_code == 422
    assert client.post(url, json={"amount": 1.001}, headers=auth_headers).status_code == 422
    assert (
        client.post(
            url, json={"amount": 10, "contributed_on": str(date.today() + timedelta(days=1))}, headers=auth_headers
        ).status_code
        == 422
    )
    assert client.post(url, json={"amount": -1}, headers=auth_headers).status_code == 400  # can't go below 0

    after_add = client.post(url, json={"amount": 600, "note": "bonus"}, headers=auth_headers).json()
    assert (after_add["saved"], after_add["remaining"], after_add["progress_pct"]) == (600, 400, 60.0)
    after_withdraw = client.post(url, json={"amount": -100}, headers=auth_headers).json()
    assert after_withdraw["saved"] == 500
    res = client.post(url, json={"amount": -600}, headers=auth_headers)
    assert res.status_code == 400 and "500.00" in res.json()["error"]["message"]

    done = client.post(url, json={"amount": 500}, headers=auth_headers).json()
    assert (done["state"], done["remaining"], done["required_per_month"]) == ("completed", 0, 0)

    listed = client.get(url, headers=auth_headers).json()
    assert [c["amount"] for c in listed["contributions"]] and listed["pagination"]["total_items"] == 3

    # Archived goals don't take contributions
    client.put(f"{API}/goals/{g['id']}", json={"status": "archived"}, headers=auth_headers)
    assert client.post(url, json={"amount": 1}, headers=auth_headers).status_code == 400


def test_deleting_contributions_never_leaves_goal_negative(client, auth_headers):
    g = client.post(f"{API}/goals", json={"name": "Phone", "target_amount": 1000}, headers=auth_headers).json()
    url = f"{API}/goals/{g['id']}/contributions"
    client.post(url, json={"amount": 300}, headers=auth_headers)
    client.post(url, json={"amount": -200}, headers=auth_headers)
    rows = {c["amount"]: c["id"] for c in client.get(url, headers=auth_headers).json()["contributions"]}
    assert client.delete(f"{url}/{rows[300]}", headers=auth_headers).status_code == 400
    assert client.delete(f"{url}/{rows[-200]}", headers=auth_headers).json()["saved"] == 300
    assert client.delete(f"{url}/{rows[-200]}", headers=auth_headers).status_code == 404


def test_delete_goal_removes_contributions_but_not_money(client, auth_headers, ids):
    inc, _ = ids
    today = date.today()
    _income(client, auth_headers, 5000, inc["Salary"], today)
    g = client.post(f"{API}/goals", json={"name": "Bike", "target_amount": 3000}, headers=auth_headers).json()
    client.post(f"{API}/goals/{g['id']}/contributions", json={"amount": 2000}, headers=auth_headers)
    month = f"{today.year:04d}-{today.month:02d}"
    assert _cashflow(client, auth_headers, month)["allocated_to_goals"] == 2000

    assert client.delete(f"{API}/goals/{g['id']}", headers=auth_headers).status_code == 204
    flow = _cashflow(client, auth_headers, month)
    assert (flow["income"], flow["saved"], flow["allocated_to_goals"], flow["unallocated"]) == (5000, 5000, 0, 5000)
    assert client.get(f"{API}/goals/{g['id']}/contributions", headers=auth_headers).status_code == 404
