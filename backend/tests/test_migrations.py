"""The models and the migrations must describe the same schema.

Catches a forgotten migration, and models that silently stop being registered
for autogenerate (Phase 5: an auto-fix removed the model imports from
alembic/env.py, which made autogenerate want to drop every table).
"""

import os
import subprocess
import sys

from app.database import Base
from tests.conftest import BACKEND_DIR, TEST_DATABASE_URL


def test_all_tables_are_registered():
    import app.models  # noqa: F401

    assert {
        "users",
        "categories",
        "expenses",
        "recurring_expenses",
        "budgets",
        "income_categories",
        "incomes",
        "savings_goals",
        "goal_contributions",
    } <= set(Base.metadata.tables)


def test_models_match_migrations():
    # A fresh process: in this one every model is already imported via the app,
    # which would hide an env.py that forgets to import them
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
