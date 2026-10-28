from app.timeutil import today as app_today
from tests.conftest import first_category_id

API = "/api/v1"


def _categories(client, headers):
    return {c["name"]: c for c in client.get(f"{API}/categories", headers=headers).json()["categories"]}


def test_create_trims_and_checks_uniqueness(client, auth_headers):
    res = client.post(f"{API}/categories", json={"name": "  Gym  ", "icon": "💪"}, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["name"] == "Gym" and res.json()["is_default"] is False
    assert client.post(f"{API}/categories", json={"name": "gym"}, headers=auth_headers).status_code == 400
    assert client.post(f"{API}/categories", json={"name": "   "}, headers=auth_headers).status_code == 422
    assert client.post(f"{API}/categories", json={"name": "x" * 101}, headers=auth_headers).status_code == 422


def test_defaults_listed_first(client, auth_headers):
    client.post(f"{API}/categories", json={"name": "Aaa"}, headers=auth_headers)
    names = [c["name"] for c in client.get(f"{API}/categories", headers=auth_headers).json()["categories"]]
    assert names[-1] == "Aaa"  # custom categories come after the defaults


def test_update_category(client, auth_headers):
    gym = client.post(f"{API}/categories", json={"name": "Gym"}, headers=auth_headers).json()
    url = f"{API}/categories/{gym['id']}"
    assert client.put(url, json={}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"name": None}, headers=auth_headers).status_code == 400
    assert client.put(url, json={"name": "random"}, headers=auth_headers).status_code == 400  # taken by a default
    renamed = client.put(url, json={"name": "Fitness", "icon": "🏋"}, headers=auth_headers).json()
    assert renamed["name"] == "Fitness" and renamed["icon"] == "🏋"
    # Renaming to its own name with different case is fine
    assert client.put(url, json={"name": "FITNESS"}, headers=auth_headers).status_code == 200
    assert (
        client.put(
            f"{API}/categories/00000000-0000-0000-0000-000000000000", json={"name": "x"}, headers=auth_headers
        ).status_code
        == 404
    )


def test_default_categories_cannot_be_deleted(client, auth_headers):
    default_id = _categories(client, auth_headers)["Random"]["id"]
    res = client.delete(f"{API}/categories/{default_id}", headers=auth_headers)
    assert res.status_code == 400
    assert "default" in res.json()["error"]["message"].lower()


def test_delete_blocked_while_in_use(client, auth_headers):
    gym = client.post(f"{API}/categories", json={"name": "Gym"}, headers=auth_headers).json()
    today = app_today()
    exp = client.post(f"{API}/expenses", json={"amount": 5, "category_id": gym["id"]}, headers=auth_headers).json()
    rec = client.post(
        f"{API}/recurring",
        json={"name": "Gym fee", "amount": 1500, "category_id": gym["id"], "frequency": "monthly", "due_day": 1},
        headers=auth_headers,
    ).json()
    bud = client.post(
        f"{API}/budgets",
        json={"category_id": gym["id"], "amount": 100, "month": today.month, "year": today.year},
        headers=auth_headers,
    ).json()

    res = client.delete(f"{API}/categories/{gym['id']}", headers=auth_headers)
    assert res.status_code == 400
    msg = res.json()["error"]["message"]
    assert "expenses" in msg and "recurring expenses" in msg and "budgets" in msg

    client.delete(f"{API}/expenses/{exp['id']}", headers=auth_headers)
    client.delete(f"{API}/recurring/{rec['id']}", headers=auth_headers)
    assert client.delete(f"{API}/categories/{gym['id']}", headers=auth_headers).status_code == 400  # budget left
    client.delete(f"{API}/budgets/{bud['id']}", headers=auth_headers)
    assert client.delete(f"{API}/categories/{gym['id']}", headers=auth_headers).status_code == 204
    assert client.delete(f"{API}/categories/{gym['id']}", headers=auth_headers).status_code == 404


def test_first_category_helper(client, auth_headers):
    assert first_category_id(client, auth_headers)
