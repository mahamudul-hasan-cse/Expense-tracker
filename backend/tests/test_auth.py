from tests.conftest import register

API = "/api/v1"


def test_register_returns_token_and_seeds_default_categories(client):
    res = client.post(f"{API}/auth/register", json={"email": "New@Example.com", "password": "longenough"})
    assert res.status_code == 201
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@example.com"
    assert "refresh_token" in res.cookies

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    names = {c["name"] for c in client.get(f"{API}/categories", headers=headers).json()["categories"]}
    assert names == {"Rickshaw", "Wifi Bill", "Random", "Smoking"}


def test_register_rejects_duplicate_email_case_insensitive(client):
    register(client, "dup@example.com")
    res = client.post(f"{API}/auth/register", json={"email": "DUP@example.com", "password": "longenough"})
    assert res.status_code == 400


def test_register_validates_email_and_password(client):
    assert (
        client.post(f"{API}/auth/register", json={"email": "not-an-email", "password": "longenough"}).status_code == 422
    )
    assert client.post(f"{API}/auth/register", json={"email": "a@example.com", "password": "short"}).status_code == 422


def test_password_is_hashed_with_argon2(client):
    from sqlalchemy import text

    from app.database import engine

    register(client, "hash@example.com", "my-secret-pass")
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar()
    assert stored.startswith("$argon2")
    assert "my-secret-pass" not in stored


def test_login_success_and_failure(client):
    register(client, "login@example.com", "right-password")
    ok = client.post(f"{API}/auth/login", json={"email": "LOGIN@example.com", "password": "right-password"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(f"{API}/auth/login", json={"email": "login@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    missing = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert missing.status_code == 401
    assert bad.json()["error"]["message"] == missing.json()["error"]["message"]


def test_me_requires_valid_token(client, auth_headers):
    assert client.get(f"{API}/auth/me", headers=auth_headers).json()["email"] == "alice@example.com"
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client):
    from app.database import SessionLocal
    from app.security import create_token
    from app.services.users import get_user_by_email

    register(client, "type@example.com")
    with SessionLocal() as db:
        user = get_user_by_email(db, "type@example.com")
        refresh, _ = create_token(user.id, "refresh", user.token_version)
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {refresh}"}).status_code == 401


def test_expired_access_token_is_rejected(client, monkeypatch):
    from app.config import get_settings

    register(client, "exp@example.com")
    monkeypatch.setattr(get_settings(), "access_token_expire_minutes", -1)
    res = client.post(f"{API}/auth/login", json={"email": "exp@example.com", "password": "correct-horse-1"})
    expired = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get(f"{API}/auth/me", headers=expired).status_code == 401


def test_refresh_issues_new_access_token(client):
    register(client, "refresh@example.com")  # sets the refresh cookie on the client
    res = client.post(f"{API}/auth/refresh")
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200


def test_refresh_without_cookie_fails(client):
    assert client.post(f"{API}/auth/refresh").status_code == 401


def test_logout_revokes_access_and_refresh_tokens(client):
    headers = register(client, "logout@example.com")
    assert client.post(f"{API}/auth/logout").status_code == 204
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert client.post(f"{API}/auth/refresh").status_code == 401
