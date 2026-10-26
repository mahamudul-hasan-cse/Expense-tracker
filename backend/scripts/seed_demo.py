"""Seed a demo user with ~3 months of realistic Bangladeshi personal-finance data.

    uv run python -m scripts.seed_demo --reset

Used for README/QA screenshots and the assistant evaluation. Deterministic (fixed
random seed), dates relative to today in Asia/Dhaka, never in the future.

Safety: refuses to run when APP_ENV=production. Only touches the demo account;
--reset deletes and recreates that one user (everything else is left alone).
"""

import argparse
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from app.config import get_settings
from app.database import SessionLocal
from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import GoalContribution, SavingsGoal
from app.models.income import Income, IncomeCategory
from app.models.recurring import RecurringExpense
from app.routers.recurring import calculate_next_due
from app.services.users import create_user, get_user_by_email
from app.timeutil import today as app_today

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@example.com")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-password-123")
DAYS = 92  # ~3 months, ending today

EXTRA_CATEGORIES = [
    ("Food", "🍛"),
    ("Groceries", "🛒"),
    ("Transport", "🚕"),
    ("Mobile Recharge", "📱"),
    ("Electricity", "⚡"),
    ("Rent", "🏠"),
    ("Health", "💊"),
]

LUNCH_SPOTS = ["Lunch at office canteen", "Kacchi Bhai", "Sultan's Dine", "Chillox burger", "দুপুরের খাবার", "Star Kabab"]
SNACKS = ["Cha & singara", "চা-বিস্কুট", "Fuchka", "Coffee at North End"]
GROCERY_SHOPS = ["Shwapno", "Agora", "Meena Bazar", "বাজার (কাঁচাবাজার)"]
RIDES = ["Uber to Gulshan", "Pathao bike", "CNG to Motijheel", "Uber Moto"]


def money(value: float) -> Decimal:
    return Decimal(str(round(value / 5) * 5))  # Taka amounts are usually round-ish


def seed(reset: bool) -> None:
    settings = get_settings()
    if settings.app_env == "production":
        sys.exit("Refusing to seed demo data with APP_ENV=production")

    rng = random.Random(42)
    today = app_today()
    start = today - timedelta(days=DAYS - 1)

    db = SessionLocal()
    try:
        existing = get_user_by_email(db, DEMO_EMAIL)
        if existing:
            if not reset:
                sys.exit(f"{DEMO_EMAIL} already exists; pass --reset to recreate it")
            db.delete(existing)  # cascades to all of the demo user's rows
            db.commit()

        user = create_user(db, DEMO_EMAIL, DEMO_PASSWORD)
        for name, icon in EXTRA_CATEGORIES:
            db.add(Category(user_id=user.id, name=name, icon=icon, is_default=False))
        db.flush()
        cat = {c.name: c for c in db.query(Category).filter(Category.user_id == user.id)}
        inc_cat = {c.name: c for c in db.query(IncomeCategory).filter(IncomeCategory.user_id == user.id)}

        def expense(day: date, amount: float, category: str, note: str | None) -> None:
            db.add(
                Expense(
                    user_id=user.id, amount=money(amount), category_id=cat[category].id, note=note, expense_date=day
                )
            )

        def income(day: date, amount: float, category: str, note: str) -> None:
            db.add(
                Income(
                    user_id=user.id,
                    amount=Decimal(str(amount)),
                    income_category_id=inc_cat[category].id,
                    note=note,
                    income_date=day,
                )
            )

        # --- Day-by-day spending ---------------------------------------------
        for offset in range(DAYS):
            day = start + timedelta(days=offset)
            weekday = day.weekday()  # 4 = Friday (weekend in Bangladesh)
            workday = weekday not in (4, 5)
            if workday:
                expense(day, rng.uniform(30, 80), "Rickshaw", "Office" if rng.random() < 0.6 else None)
                expense(day, rng.uniform(140, 380), "Food", rng.choice(LUNCH_SPOTS))
            if rng.random() < 0.55:
                expense(day, rng.uniform(25, 90), "Random", rng.choice(SNACKS))
            if rng.random() < 0.18:
                expense(day, rng.uniform(220, 650), "Transport", rng.choice(RIDES))
            if weekday == 4:  # Friday market run
                expense(day, rng.uniform(1400, 3200), "Groceries", rng.choice(GROCERY_SHOPS))
            if rng.random() < 0.3:
                expense(day, rng.uniform(20, 60), "Smoking", None)
            if day.day == 1:
                expense(day, 15000, "Rent", "House rent, Mirpur")
            if day.day == 10:
                expense(day, 1000, "Wifi Bill", "Link3 monthly")
            if day.day in (5, 20):
                expense(day, rng.uniform(700, 1300), "Electricity", "DESCO prepaid")
            if day.day in (3, 17):
                expense(day, rng.choice([199, 299, 499]), "Mobile Recharge", "GP internet pack")
            if rng.random() < 0.04:
                expense(day, rng.uniform(400, 2200), "Health", "Pharmacy")

        # One unusual purchase for "detect unusual spending"
        expense(today - timedelta(days=12), 8500, "Random", "Eid shopping, Bashundhara City")

        # --- Income ----------------------------------------------------------
        month_starts = sorted({(start + timedelta(days=i)).replace(day=1) for i in range(DAYS)})
        for first in month_starts:
            if start <= first <= today:
                income(first, 55000, "Salary", "Monthly salary")
        for offset in (18, 47, 75):
            if offset < DAYS:
                income(
                    start + timedelta(days=offset), rng.choice([8000, 12000, 15000]), "Freelance", "Upwork logo project"
                )
        income(today - timedelta(days=13), 5000, "Gift", "Eid salami")

        # --- Budgets for the current month -----------------------------------
        for name, amount in [
            ("Food", 7000),
            ("Rickshaw", 1800),
            ("Groceries", 9000),
            ("Random", 3000),
            ("Transport", 2500),
        ]:
            db.add(
                Budget(
                    user_id=user.id,
                    category_id=cat[name].id,
                    amount=Decimal(amount),
                    month=today.month,
                    year=today.year,
                )
            )

        # --- Recurring items ---------------------------------------------------
        recurring = [
            ("expense", "House rent", 15000, "Rent", "monthly", 1),
            ("expense", "Link3 wifi", 1000, "Wifi Bill", "monthly", 10),
            ("expense", "GP internet pack", 499, "Mobile Recharge", "monthly", min(today.day + 3, 28)),
            ("income", "Salary", 55000, "Salary", "monthly", 1),
            ("income", "Weekend tuition", 3000, "Other", "weekly", ((today.weekday() + 2) % 7) + 1),
        ]
        for kind, name, amount, category, frequency, due_day in recurring:
            rec = RecurringExpense(
                user_id=user.id,
                kind=kind,
                name=name,
                amount=Decimal(amount),
                category_id=cat[category].id if kind == "expense" else None,
                income_category_id=inc_cat[category].id if kind == "income" else None,
                frequency=frequency,
                due_day=due_day,
            )
            # Rent and salary for this month are already paid/received (recorded above)
            if name in ("House rent", "Salary") and today.day >= 1:
                rec.last_paid_on = calculate_next_due(frequency, due_day, today.replace(day=1))
            db.add(rec)

        # --- Savings goals -----------------------------------------------------
        laptop = SavingsGoal(
            user_id=user.id,
            name="New laptop",
            icon="💻",
            target_amount=Decimal(95000),
            target_date=today + timedelta(days=240),
        )
        emergency = SavingsGoal(user_id=user.id, name="Emergency fund", icon="🛟", target_amount=Decimal(150000))
        db.add_all([laptop, emergency])
        db.flush()
        for offset, goal, amount in [
            (5, laptop, 6000),
            (35, laptop, 6000),
            (65, laptop, 8000),
            (6, emergency, 10000),
            (36, emergency, 10000),
            (66, emergency, 5000),
        ]:
            if offset < DAYS:
                db.add(
                    GoalContribution(
                        goal_id=goal.id,
                        user_id=user.id,
                        amount=Decimal(amount),
                        contributed_on=start + timedelta(days=offset),
                    )
                )

        db.commit()
        counts = {
            "expenses": db.query(Expense).filter(Expense.user_id == user.id).count(),
            "incomes": db.query(Income).filter(Income.user_id == user.id).count(),
            "budgets": len([1 for _ in db.query(Budget).filter(Budget.user_id == user.id)]),
        }
        print(f"Seeded {DEMO_EMAIL} ({start} .. {today}): {counts}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.seed_demo")
    parser.add_argument("--reset", action="store_true", help="delete and recreate the demo user if it exists")
    seed(parser.parse_args().reset)


if __name__ == "__main__":
    main()
