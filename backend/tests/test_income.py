import csv
import io
from datetime import date, timedelta

import pytest

from app.timeutil import today as app_today

API = "/api/v1"


def income_categories(client, headers):
    res = client.get(f"{API}/income-categories", headers=headers)
    assert res.status_code == 200
    return {c["name"]: c for c in res.json()["income_categories"]}


def add_income(client, headers, amount, category_id, when=None, note=None):
    body = {"amount": amount, "income_category_id": category_id}
    if when is not None:
        body["income_date"] = str(when)
    if note is not None:
        body["note"] = note
    res = client.post(f"{API}/incomes", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# --- Income categories -------------------------------------------------------


def test_other_income_category_icon_is_not_a_plus_sign(client, auth_headers):
    """➕ looked like an "add" button in the dashboard's Upcoming list."""
    assert income_categories(client, auth_headers)["Other"]["icon"] == "💰"


def test_defaults_seeded_on_registration(client, auth_headers):
    cats = income_categories(client, auth_headers)
    assert set(cats) == {"Salary", "Freelance", "Business", "Gift", "Other"}
    assert all(c["is_default"] for c in cats.values())


def test_user_defined_income_category_crud(client, auth_headers):
    created = client.post(f"{API}/income-categories", json={"name": " Tuition ", "icon": "📚"}, headers=auth_headers)
    assert created.status_code == 201 and created.json()["name"] == "Tuition"
    cid = created.json()["id"]
    assert client.post(f"{API}/income-categories", json={"name": "tuition"}, headers=auth_headers).status_code == 400
    assert (
        client.put(f"{API}/income-categories/{cid}", json={"name": "salary"}, headers=auth_headers).status_code == 400
    )
    assert client.put(f"{API}/income-categories/{cid}", json={}, headers=auth_headers).status_code == 400
    assert client.put(f"{API}/income-categories/{cid}", json={"name": None}, headers=auth_headers).status_code == 400
    assert (
        client.put(f"{API}/income-categories/{cid}", json={"name": "Tutoring"}, headers=auth_headers).json()["name"]
        == "Tutoring"
    )
    assert client.delete(f"{API}/income-categories/{cid}", headers=auth_headers).status_code == 204
    assert client.delete(f"{API}/income-categories/{cid}", headers=auth_headers).status_code == 404


def test_income_category_delete_rules(client, auth_headers):
    cats = income_categories(client, auth_headers)
    assert client.delete(f"{API}/income-categories/{cats['Salary']['id']}", headers=auth_headers).status_code == 400
    custom = client.post(f"{API}/income-categories", json={"name": "Rent in"}, headers=auth_headers).json()
    inc = add_income(client, auth_headers, 100, custom["id"])
    rec = client.post(
        f"{API}/recurring",
        json={
            "kind": "income",
            "name": "Flat rent",
            "amount": 5000,
            "income_category_id": custom["id"],
            "frequency": "monthly",
            "due_day": 1,
        },
        headers=auth_headers,
    ).json()
    res = client.delete(f"{API}/income-categories/{custom['id']}", headers=auth_headers)
    assert res.status_code == 400
    assert "income entries" in res.json()["error"]["message"] and "recurring income" in res.json()["error"]["message"]
    client.delete(f"{API}/incomes/{inc['id']}", headers=auth_headers)
    client.delete(f"{API}/recurring/{rec['id']}", headers=auth_headers)
    assert client.delete(f"{API}/income-categories/{custom['id']}", headers=auth_headers).status_code == 204


# --- Income entries ----------------------------------------------------------


@pytest.mark.parametrize(
    "amount, status",
    [(0.01, 201), (99_999_999.99, 201), (0, 422), (-1, 422), (1.234, 422), (100_000_000, 422)],
)
def test_income_amount_uses_expense_money_rules(client, auth_headers, amount, status):
    cid = income_categories(client, auth_headers)["Salary"]["id"]
    assert (
        client.post(
            f"{API}/incomes", json={"amount": amount, "income_category_id": cid}, headers=auth_headers
        ).status_code
        == status
    )


def test_income_date_rules(client, auth_headers):
    cid = income_categories(client, auth_headers)["Salary"]["id"]
    tomorrow = app_today() + timedelta(days=1)
    assert (
        client.post(
            f"{API}/incomes",
            json={"amount": 1, "income_category_id": cid, "income_date": str(tomorrow)},
            headers=auth_headers,
        ).status_code
        == 422
    )
    assert add_income(client, auth_headers, 1, cid)["income_date"] == str(app_today())


def test_income_crud_and_listing(client, auth_headers):
    cats = income_categories(client, auth_headers)
    salary = add_income(client, auth_headers, 50000, cats["Salary"]["id"], date(2026, 3, 1), "March salary")
    add_income(client, auth_headers, 3000, cats["Gift"]["id"], date(2026, 3, 10), "Eid salami")
    add_income(client, auth_headers, 8000, cats["Freelance"]["id"], date(2026, 2, 20), "logo_design")

    listed = client.get(f"{API}/incomes", headers=auth_headers).json()
    assert [i["amount"] for i in listed["incomes"]] == [3000, 50000, 8000]
    assert listed["pagination"]["total_items"] == 3
    march = client.get(f"{API}/incomes?start_date=2026-03-01&end_date=2026-03-31", headers=auth_headers).json()
    assert {i["note"] for i in march["incomes"]} == {"March salary", "Eid salami"}
    by_cat = client.get(f"{API}/incomes?income_category_id={cats['Gift']['id']}", headers=auth_headers).json()
    assert [i["note"] for i in by_cat["incomes"]] == ["Eid salami"]
    assert [i["note"] for i in client.get(f"{API}/incomes?search=_", headers=auth_headers).json()["incomes"]] == [
        "logo_design"
    ]
    assert [
        i["amount"] for i in client.get(f"{API}/incomes?sort=amount_asc", headers=auth_headers).json()["incomes"]
    ] == [3000, 8000, 50000]

    url = f"{API}/incomes/{salary['id']}"
    assert client.put(url, json={}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"amount": None}, headers=auth_headers).status_code == 400
    assert (
        client.put(
            url, json={"income_category_id": "00000000-0000-0000-0000-000000000000"}, headers=auth_headers
        ).status_code
        == 400
    )
    updated = client.put(url, json={"amount": 52000, "note": None}, headers=auth_headers).json()
    assert updated["amount"] == 52000 and updated["note"] is None and updated["category"]["name"] == "Salary"
    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.put(url, json={"amount": 1}, headers=auth_headers).status_code == 404


def test_csv_export_includes_income(client, auth_headers):
    cid = income_categories(client, auth_headers)["Salary"]["id"]
    ecat = client.get(f"{API}/categories", headers=auth_headers).json()["categories"][0]
    add_income(client, auth_headers, 50000, cid, date(2026, 3, 1), "March salary")
    client.post(
        f"{API}/expenses",
        json={"amount": 30, "category_id": ecat["id"], "expense_date": "2026-03-01"},
        headers=auth_headers,
    )
    client.post(
        f"{API}/expenses",
        json={"amount": 99, "category_id": ecat["id"], "expense_date": "2026-03-05"},
        headers=auth_headers,
    )
    rows = list(
        csv.reader(
            io.StringIO(
                client.get(f"{API}/export/csv?start_date=2026-03-01&end_date=2026-03-31", headers=auth_headers).text
            )
        )
    )
    assert rows[0] == ["Date", "Amount", "Category", "Note", "Type"]
    assert [(r[0], r[1], r[4]) for r in rows[1:]] == [
        ("2026-03-05", "99.00", "Expense"),
        ("2026-03-01", "30.00", "Expense"),
        ("2026-03-01", "50000.00", "Income"),
    ]
