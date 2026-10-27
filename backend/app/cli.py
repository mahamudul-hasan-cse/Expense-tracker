"""Admin commands.

    uv run python -m app.cli set-password <email> [--new-email <email>]
    uv run python -m app.cli assistant-usage [--days 7]

Sets (and optionally changes the email of) an existing account, e.g. the owner
account created by the add_users_and_ownership migration.
"""

import argparse
import getpass
import sys
from datetime import timedelta

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


def assistant_usage(days: int) -> int:
    """Per-day assistant usage and cost (Asia/Dhaka days), plus the top users by cost.

    Grouped in Python with zoneinfo, so it doesn't depend on the database knowing
    time-zone names.
    """
    from collections import defaultdict
    from datetime import datetime, time
    from decimal import Decimal

    from app.models.assistant import AssistantUsage
    from app.models.user import User
    from app.timeutil import app_timezone
    from app.timeutil import today as app_today

    tz = app_timezone()
    since = datetime.combine(app_today() - timedelta(days=days - 1), time.min, tzinfo=tz)
    db = SessionLocal()
    try:
        rows = (
            db.query(AssistantUsage, User.email)
            .join(User, User.id == AssistantUsage.user_id)
            .filter(AssistantUsage.created_at >= since)
            .all()
        )
        per_day: dict = defaultdict(
            lambda: {"requests": 0, "users": set(), "prompt": 0, "output": 0, "cost": Decimal("0"), "errors": 0}
        )
        per_user: dict = defaultdict(lambda: {"cost": Decimal("0"), "requests": 0})
        for usage, email in rows:
            day = per_day[usage.created_at.astimezone(tz).date()]
            day["requests"] += 1
            day["users"].add(usage.user_id)
            day["prompt"] += usage.prompt_tokens
            day["output"] += usage.completion_tokens
            day["cost"] += usage.cost_usd
            day["errors"] += usage.status != "ok"
            per_user[email]["cost"] += usage.cost_usd
            per_user[email]["requests"] += 1

        print(f"Assistant usage, last {days} day(s) (Asia/Dhaka):")
        print(
            f"{'day':<12}{'requests':>9}{'users':>7}{'prompt tok':>12}{'output tok':>12}{'cost USD':>11}{'errors':>8}"
        )
        total = Decimal("0")
        for d in sorted(per_day):
            v = per_day[d]
            total += v["cost"]
            print(
                f"{d!s:<12}{v['requests']:>9}{len(v['users']):>7}{v['prompt']:>12}{v['output']:>12}{float(v['cost']):>11.4f}{v['errors']:>8}"
            )
        print(f"{'total':<12}{'':>9}{'':>7}{'':>12}{'':>12}{float(total):>11.4f}")

        top = sorted(per_user.items(), key=lambda kv: kv[1]["cost"], reverse=True)[:5]
        if top:
            print("\nTop users by cost:")
            for email, v in top:
                print(f"  {email:<40} {float(v['cost']):>9.4f} USD  ({v['requests']} requests)")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("set-password", help="Set an account's password")
    sp.add_argument("email")
    sp.add_argument("--new-email")
    usage = sub.add_parser("assistant-usage", help="Show AI assistant usage and cost per day")
    usage.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if args.command == "set-password":
        return set_password(args.email, args.new_email)
    if args.command == "assistant-usage":
        return assistant_usage(max(1, args.days))
    return 1


if __name__ == "__main__":
    sys.exit(main())
