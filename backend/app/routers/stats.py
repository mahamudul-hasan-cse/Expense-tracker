from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring import RecurringExpense
from app.models.user import User
from app.routers.recurring import next_unpaid_due
from app.schemas.stats import (
    CashflowResponse,
    CategoryBreakdown,
    DailyTotal,
    StatsSummary,
    UpcomingReminder,
    UpcomingReminderListResponse,
)
from app.services.cashflow import get_cashflow, month_bounds
from app.timeutil import today as app_today

router = APIRouter(prefix="/stats", tags=["Statistics"])


def get_period_dates(period: str, reference_date: date) -> tuple[date, date]:
    """Calculate start and end dates for a period."""
    if period == "weekly":
        # Week starts on Monday
        start = reference_date - timedelta(days=reference_date.weekday())
        end = start + timedelta(days=6)
    else:  # monthly
        start = date(reference_date.year, reference_date.month, 1)
        # Last day of month
        if reference_date.month == 12:
            end = date(reference_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(reference_date.year, reference_date.month + 1, 1) - timedelta(days=1)
    return start, end


@router.get("/summary", response_model=StatsSummary)
def get_stats_summary(
    period: Literal["weekly", "monthly"] = "monthly",
    ref_date: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get spending summary for a period."""
    reference_date = ref_date or app_today()
    start_date, end_date = get_period_dates(period, reference_date)

    # Get expenses in the period
    expenses = (
        db.query(Expense)
        .options(joinedload(Expense.category))
        .filter(
            Expense.user_id == current_user.id, Expense.expense_date >= start_date, Expense.expense_date <= end_date
        )
        .all()
    )

    # Calculate totals
    total_spent = sum((exp.amount for exp in expenses), Decimal("0"))

    # Group by category: (category, total, count)
    category_totals: dict[str, tuple[Category, Decimal, int]] = {}
    for exp in expenses:
        cat_id = str(exp.category_id)
        _, total, count = category_totals.get(cat_id, (exp.category, Decimal("0"), 0))
        category_totals[cat_id] = (exp.category, total + exp.amount, count + 1)

    # Calculate percentages
    by_category = []
    for cat_id, (category, total, count) in category_totals.items():
        percentage = float(total / total_spent * 100) if total_spent > 0 else 0
        by_category.append(
            CategoryBreakdown(
                category_id=cat_id,
                category_name=category.name,
                category_icon=category.icon,
                total=total,
                percentage=round(percentage, 1),
                count=count,
            )
        )

    # Sort by total descending
    by_category.sort(key=lambda x: x.total, reverse=True)

    # Calculate daily totals
    daily_map = {}
    current = start_date
    while current <= end_date:
        daily_map[current] = Decimal("0")
        current += timedelta(days=1)

    for exp in expenses:
        if exp.expense_date in daily_map:
            daily_map[exp.expense_date] += exp.amount

    daily_totals = [DailyTotal(date=d, total=t) for d, t in sorted(daily_map.items())]

    return StatsSummary(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_spent=total_spent,
        by_category=by_category,
        daily_totals=daily_totals,
    )


@router.get("/upcoming-recurring", response_model=UpcomingReminderListResponse)
def get_upcoming_recurring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recurring bills and income due within the next 7 days (not yet marked paid)."""
    today = app_today()
    week_later = today + timedelta(days=7)

    recurring_list = (
        db.query(RecurringExpense)
        .options(joinedload(RecurringExpense.category), joinedload(RecurringExpense.income_category))
        .filter(RecurringExpense.user_id == current_user.id, RecurringExpense.is_active.is_(True))
        .all()
    )

    upcoming = []
    for rec in recurring_list:
        next_due = next_unpaid_due(rec.frequency, rec.due_day, rec.last_paid_on, today)

        if today <= next_due <= week_later:
            days_until = (next_due - today).days
            category = rec.category if rec.kind == "expense" else rec.income_category
            upcoming.append(
                UpcomingReminder(
                    id=str(rec.id),
                    kind=rec.kind,
                    name=rec.name,
                    amount=rec.amount,
                    due_date=next_due,
                    days_until=days_until,
                    category={"name": category.name, "icon": category.icon} if category else {"name": "", "icon": None},
                )
            )

    # Sort by days_until
    upcoming.sort(key=lambda x: x.days_until)

    return UpcomingReminderListResponse(upcoming=upcoming)


@router.get("/cashflow", response_model=CashflowResponse)
def get_cashflow_summary(
    month: Optional[str] = Query(None, description="YYYY-MM; defaults to the current month (Asia/Dhaka)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Income, spending, saved (income − spending) and savings rate for a month."""
    try:
        label, start, end = month_bounds(month)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    flow = get_cashflow(db, current_user.id, start, end)
    return CashflowResponse(
        month=label,
        start_date=start,
        end_date=end,
        income=flow.income,
        spent=flow.spent,
        saved=flow.saved,
        savings_rate=flow.savings_rate,
        allocated_to_goals=flow.allocated_to_goals,
        unallocated=flow.unallocated,
    )
