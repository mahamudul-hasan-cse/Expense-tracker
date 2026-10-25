from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional, Literal
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
    name: str
    amount: Money
    due_date: date
    days_until: int
    category: dict  # {"name": str, "icon": str|None}


class UpcomingReminderListResponse(BaseModel):
    upcoming: list[UpcomingReminder]
