import pytest

from app import cli
from app.database import SessionLocal
from app.security import verify_password
from app.services.users import get_user_by_email
from tests.conftest import register


def _prompts(monkeypatch, *answers):
    it = iter(answers)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(it))


def test_set_password_and_rename(client, monkeypatch):
    register(client, "owner@example.com", "old-password")
    _prompts(monkeypatch, "brand-new-pass", "brand-new-pass")
    assert cli.set_password("owner@example.com", "Me@Example.com") == 0
    with SessionLocal() as db:
        assert get_user_by_email(db, "owner@example.com") is None
        user = get_user_by_email(db, "me@example.com")
        assert verify_password(user.password_hash, "brand-new-pass")
        assert user.token_version == 1  # existing sessions signed out


@pytest.mark.parametrize(
    "answers, new_email",
    [
        (("short", "short"), None),
        (("long-enough-1", "different-2"), None),
        (("long-enough-1", "long-enough-1"), "taken@example.com"),
    ],
)
def test_set_password_rejections(client, monkeypatch, answers, new_email):
    register(client, "owner@example.com")
    register(client, "taken@example.com")
    _prompts(monkeypatch, *answers)
    assert cli.set_password("owner@example.com", new_email) == 1


def test_set_password_unknown_user(client, monkeypatch):
    _prompts(monkeypatch)
    assert cli.set_password("ghost@example.com", None) == 1
