"""Model registry.

Importing this package registers every table on Base.metadata. Alembic's env.py
imports it so autogenerate sees all models; add new models here.
"""

from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring import RecurringExpense
from app.models.user import User

__all__ = ["Budget", "Category", "Expense", "RecurringExpense", "User"]
