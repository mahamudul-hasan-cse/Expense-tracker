from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.types import Money


class CategoryBreakdown(BaseModel):
    category_id: str
    category_name: str
    category_icon: Optional[str]
    total: Money
    percentage: float
    count: int


class DailyTotal(BaseModel):
    date: date
    total: Money


class StatsSummary(BaseModel):
    period: Literal["weekly", "monthly"]
    start_date: date
    end_date: date
    total_spent: Money
    by_category: list[CategoryBreakdown]
    daily_totals: list[DailyTotal]


class UpcomingReminder(BaseModel):
    id: str
    kind: Literal["expense", "income"]
    name: str
    amount: Money
    due_date: date
    days_until: int
    category: dict  # {"name": str, "icon": str|None}


class UpcomingReminderListResponse(BaseModel):
    upcoming: list[UpcomingReminder]


class CashflowResponse(BaseModel):
    """Money in vs out for a month. Goal contributions are allocations of
    savings, so they never change `spent` or `saved`."""

    month: str  # YYYY-MM
    start_date: date
    end_date: date
    income: Money
    spent: Money
    saved: Money  # income - spent; negative means overspent
    savings_rate: Optional[float]  # saved / income * 100; null when there is no income
    allocated_to_goals: Money
    unallocated: Money
