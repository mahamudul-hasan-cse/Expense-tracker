"""Money in vs money out. Shared by the API and (later) the assistant's tools."""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.goal import GoalContribution
from app.models.income import Income
from app.timeutil import today as app_today

_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


@dataclass(frozen=True)
class Cashflow:
    start_date: date
    end_date: date
    income: Decimal
    spent: Decimal
    allocated_to_goals: Decimal

    @property
    def saved(self) -> Decimal:
        """Income minus expenses. Negative = overspent. Contributions don't count."""
        return self.income - self.spent

    @property
    def savings_rate(self) -> Optional[float]:
        """Percent of income saved; None (shown as "—") when there was no income."""
        if self.income <= 0:
            return None
        return round(float(self.saved / self.income * 100), 1)

    @property
    def unallocated(self) -> Decimal:
        return self.saved - self.allocated_to_goals


def month_bounds(month: Optional[str]) -> tuple[str, date, date]:
    """Parse "YYYY-MM" (default: current month in Asia/Dhaka) into (label, first day, last day)."""
    if month is None:
        today = app_today()
        year, mon = today.year, today.month
    else:
        match = _MONTH_RE.match(month)
        if not match:
            raise ValueError("month must be YYYY-MM")
        year, mon = int(match.group(1)), int(match.group(2))
    last = calendar.monthrange(year, mon)[1]
    return f"{year:04d}-{mon:02d}", date(year, mon, 1), date(year, mon, last)


def _sum(db: Session, column, *filters) -> Decimal:
    value = db.query(func.coalesce(func.sum(column), 0)).filter(*filters).scalar()
    return Decimal(value)


def get_cashflow(db: Session, user_id: UUID, start: date, end: date) -> Cashflow:
    """Totals for [start, end] inclusive, all computed in SQL."""
    return Cashflow(
        start_date=start,
        end_date=end,
        income=_sum(
            db, Income.amount, Income.user_id == user_id, Income.income_date >= start, Income.income_date <= end
        ),
        spent=_sum(
            db, Expense.amount, Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end
        ),
        allocated_to_goals=_sum(
            db,
            GoalContribution.amount,
            GoalContribution.user_id == user_id,
            GoalContribution.contributed_on >= start,
            GoalContribution.contributed_on <= end,
        ),
    )
