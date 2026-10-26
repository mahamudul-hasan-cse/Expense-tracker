import csv
import io
from datetime import date

import pytest

API = "/api/v1"


@pytest.fixture
def cats(client, auth_headers):
    return {c["name"]: c["id"] for c in client.get(f"{API}/categories", headers=auth_headers).json()["categories"]}


def add(client, headers, amount, category_id, when, note=None):
    res = client.post(
        f"{API}/expenses",
        json={"amount": amount, "category_id": category_id, "expense_date": str(when), "note": note},
        headers=headers,
    )
    assert res.status_code == 201, res.text


# --- Stats -------------------------------------------------------------------


def test_monthly_summary_totals_and_breakdown(client, auth_headers, cats):
    ref = date(2026, 3, 15)
    add(client, auth_headers, 100, cats["Rickshaw"], date(2026, 3, 1))
    add(client, auth_headers, 50.5, cats["Rickshaw"], date(2026, 3, 1))
    add(client, auth_headers, 300, cats["Wifi Bill"], date(2026, 3, 31))
    add(client, auth_headers, 999, cats["Random"], date(2026, 2, 28))  # previous month: excluded

    s = client.get(f"{API}/stats/summary?period=monthly&date={ref}", headers=auth_headers).json()
    assert (s["start_date"], s["end_date"]) == ("2026-03-01", "2026-03-31")
    assert s["total_spent"] == 450.5
    by_cat = {c["category_name"]: c for c in s["by_category"]}
    assert by_cat["Wifi Bill"]["total"] == 300 and by_cat["Wifi Bill"]["count"] == 1
    assert by_cat["Rickshaw"]["total"] == 150.5 and by_cat["Rickshaw"]["percentage"] == 33.4
    assert [c["category_name"] for c in s["by_category"]] == ["Wifi Bill", "Rickshaw"]  # sorted by total
    assert len(s["daily_totals"]) == 31
    assert s["daily_totals"][0] == {"date": "2026-03-01", "total": 150.5}
    assert s["daily_totals"][1]["total"] == 0


def test_weekly_summary_runs_monday_to_sunday(client, auth_headers, cats):
    # 2026-03-11 is a Wednesday -> week of Mon 03-09 .. Sun 03-15
    add(client, auth_headers, 20, cats["Random"], date(2026, 3, 9))
    add(client, auth_headers, 30, cats["Random"], date(2026, 3, 15))
    add(client, auth_headers, 40, cats["Random"], date(2026, 3, 16))  # next week
    s = client.get(f"{API}/stats/summary?period=weekly&date=2026-03-11", headers=auth_headers).json()
    assert (s["start_date"], s["end_date"]) == ("2026-03-09", "2026-03-15")
    assert s["total_spent"] == 50
    assert len(s["daily_totals"]) == 7


def test_december_summary_and_empty_period(client, auth_headers):
    s = client.get(f"{API}/stats/summary?period=monthly&date=2025-12-10", headers=auth_headers).json()
    assert (s["start_date"], s["end_date"]) == ("2025-12-01", "2025-12-31")
    assert s["total_spent"] == 0 and s["by_category"] == []
    assert client.get(f"{API}/stats/summary?period=yearly", headers=auth_headers).status_code == 422


# --- Budgets -----------------------------------------------------------------


def test_budget_spent_percentage_and_summary(client, auth_headers, cats):
    add(client, auth_headers, 400, cats["Rickshaw"], date(2026, 3, 2))
    add(client, auth_headers, 100, cats["Rickshaw"], date(2026, 3, 31))
    add(client, auth_headers, 700, cats["Rickshaw"], date(2026, 4, 1))  # other month
    add(client, auth_headers, 60, cats["Random"], date(2026, 3, 5))

    r = client.post(
        f"{API}/budgets",
        json={"category_id": cats["Rickshaw"], "amount": 1000, "month": 3, "year": 2026},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert (r.json()["spent"], r.json()["percentage"]) == (500, 50.0)
    client.post(
        f"{API}/budgets",
        json={"category_id": cats["Random"], "amount": 50, "month": 3, "year": 2026},
        headers=auth_headers,
    )

    summary = client.get(f"{API}/budgets/summary?month=3&year=2026", headers=auth_headers).json()
    assert summary["total_budget"] == 1050 and summary["total_spent"] == 560
    assert summary["percentage"] == 53.3
    over = {b["category"]["name"]: b for b in summary["budgets"]}["Random"]
    assert over["percentage"] == 120.0  # over budget is reported, not capped


def test_budget_rules(client, auth_headers, cats):
    body = {"category_id": cats["Rickshaw"], "amount": 100, "month": 3, "year": 2026}
    created = client.post(f"{API}/budgets", json=body, headers=auth_headers).json()
    assert client.post(f"{API}/budgets", json=body, headers=auth_headers).status_code == 400  # duplicate month
    for bad in ({"amount": 0}, {"month": 13}, {"year": 2019}, {"amount": 1.001}):
        assert client.post(f"{API}/budgets", json={**body, **bad}, headers=auth_headers).status_code == 422
    assert (
        client.post(
            f"{API}/budgets", json={**body, "category_id": "00000000-0000-0000-0000-000000000000"}, headers=auth_headers
        ).status_code
        == 400
    )

    url = f"{API}/budgets/{created['id']}"
    assert client.put(url, json={"amount": 250}, headers=auth_headers).json()["amount"] == 250
    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.put(url, json={"amount": 1}, headers=auth_headers).status_code == 404
    assert client.delete(url, headers=auth_headers).status_code == 404


def test_budget_defaults_to_current_month(client, auth_headers, cats):
    today = date.today()
    client.post(
        f"{API}/budgets",
        json={"category_id": cats["Random"], "amount": 10, "month": today.month, "year": today.year},
        headers=auth_headers,
    )
    assert len(client.get(f"{API}/budgets", headers=auth_headers).json()["budgets"]) == 1
    assert client.get(f"{API}/budgets/summary", headers=auth_headers).json()["total_budget"] == 10


# --- CSV export --------------------------------------------------------------


def test_csv_export(client, auth_headers, cats):
    add(client, auth_headers, 350, cats["Random"], date(2026, 1, 17), note='Lunch, "Chillox"')
    add(client, auth_headers, 30, cats["Rickshaw"], date(2026, 1, 18))
    add(client, auth_headers, 5, cats["Rickshaw"], date(2026, 2, 1))  # outside range

    res = client.get(f"{API}/export/csv?start_date=2026-01-01&end_date=2026-01-31", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "expenses_2026-01-01_2026-01-31.csv" in res.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(res.text)))
    assert rows[0] == ["Date", "Amount", "Category", "Note"]
    assert rows[1:] == [
        ["2026-01-18", "30.00", "Rickshaw", ""],
        ["2026-01-17", "350.00", "Random", 'Lunch, "Chillox"'],  # quoting round-trips
    ]


def test_csv_export_validates_range(client, auth_headers):
    assert (
        client.get(f"{API}/export/csv?start_date=2026-02-01&end_date=2026-01-01", headers=auth_headers).status_code
        == 400
    )
    assert client.get(f"{API}/export/csv?start_date=2026-02-01", headers=auth_headers).status_code == 422
