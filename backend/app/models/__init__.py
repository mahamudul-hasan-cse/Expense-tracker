"""Model registry.

Importing this package registers every table on Base.metadata. Alembic's env.py
imports it so autogenerate sees all models; add new models here.
"""

from app.models.assistant import AssistantConversation, AssistantInsight, AssistantMessage, AssistantUsage
from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import GoalContribution, SavingsGoal
from app.models.income import Income, IncomeCategory
from app.models.recurring import RecurringExpense
from app.models.user import User

__all__ = [
    "AssistantConversation",
    "AssistantInsight",
    "AssistantMessage",
    "AssistantUsage",
    "Budget",
    "Category",
    "Expense",
    "GoalContribution",
    "Income",
    "IncomeCategory",
    "RecurringExpense",
    "SavingsGoal",
    "User",
]
