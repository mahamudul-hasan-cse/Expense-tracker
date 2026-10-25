"""Test setup: runs against a separate Postgres database.

Set TEST_DATABASE_URL to point at it (default: wallet_agent_test on localhost).
The schema is rebuilt from the Alembic migrations once per session, and every
table is truncated between tests.
"""
import os
from pathlib import Path

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent_test",
)
# Must be set before the app (and its cached settings) is imported
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
TABLES = "users, categories, expenses, recurring_expenses, budgets"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Run all migrations down to base and back up, which also tests downgrades."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # Empty leftovers from a previous run first: downgrading restores the global
    # unique category name, which per-user duplicates would violate
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str, password: str = "correct-horse-1") -> dict:
    """Register a user and return Authorization headers for them."""
    res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return register(client, "alice@example.com")


@pytest.fixture
def other_headers(client):
    return register(client, "bob@example.com")


def first_category_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/categories", headers=headers).json()["categories"][0]["id"]
