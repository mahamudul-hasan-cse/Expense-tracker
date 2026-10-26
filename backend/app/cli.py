"""Admin commands.

    uv run python -m app.cli set-password <email> [--new-email <email>]

Sets (and optionally changes the email of) an existing account, e.g. the owner
account created by the add_users_and_ownership migration.
"""

import argparse
import getpass
import sys

from app.database import SessionLocal
from app.security import hash_password
from app.services.users import get_user_by_email


def set_password(email: str, new_email: str | None) -> int:
    db = SessionLocal()
    try:
        user = get_user_by_email(db, email)
        if user is None:
            print(f"No user with email {email}", file=sys.stderr)
            return 1

        password = getpass.getpass("New password (min 8 chars): ")
        if len(password) < 8:
            print("Password must be at least 8 characters", file=sys.stderr)
            return 1
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match", file=sys.stderr)
            return 1

        if new_email:
            if get_user_by_email(db, new_email):
                print(f"Email {new_email} is already taken", file=sys.stderr)
                return 1
            user.email = new_email.strip().lower()
        user.password_hash = hash_password(password)
        user.token_version += 1  # sign out existing sessions
        db.commit()
        print(f"Updated {user.email}")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("set-password", help="Set an account's password")
    sp.add_argument("email")
    sp.add_argument("--new-email")
    args = parser.parse_args()
    if args.command == "set-password":
        return set_password(args.email, args.new_email)
    return 1


if __name__ == "__main__":
    sys.exit(main())
