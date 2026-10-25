from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, Literal
from datetime import date, timedelta
from decimal import Decimal

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.expense import Expense
from app.models.category import Category
from app.models.recurring import RecurringExpense
from app.schemas.stats import (
    StatsSummary,
    CategoryBreakdown,
    DailyTotal,
    UpcomingReminder,
    UpcomingReminderListResponse,
)
from app.routers.recurring import calculate_next_due

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
    reference_date = ref_date or date.today()
    start_date, end_date = get_period_dates(period, reference_date)
    
    # Get expenses in the period
    expenses = db.query(Expense).options(
        joinedload(Expense.category)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    ).all()
    
    # Calculate totals
    total_spent = sum(exp.amount for exp in expenses)
    
    # Group by category
    category_totals = {}
    for exp in expenses:
        cat_id = str(exp.category_id)
        if cat_id not in category_totals:
            category_totals[cat_id] = {
                "category_id": cat_id,
                "category_name": exp.category.name,
                "category_icon": exp.category.icon,
                "total": Decimal("0"),
                "count": 0
            }
        category_totals[cat_id]["total"] += exp.amount
        category_totals[cat_id]["count"] += 1
    
    # Calculate percentages
    by_category = []
    for cat_data in category_totals.values():
        percentage = float(cat_data["total"] / total_spent * 100) if total_spent > 0 else 0
        by_category.append(CategoryBreakdown(
            category_id=cat_data["category_id"],
            category_name=cat_data["category_name"],
            category_icon=cat_data["category_icon"],
            total=cat_data["total"],
            percentage=round(percentage, 1),
            count=cat_data["count"]
        ))
    
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
    
    daily_totals = [
        DailyTotal(date=d, total=t)
        for d, t in sorted(daily_map.items())
    ]
    
    return StatsSummary(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_spent=total_spent,
        by_category=by_category,
        daily_totals=daily_totals
    )


@router.get("/upcoming-recurring", response_model=UpcomingReminderListResponse)
def get_upcoming_recurring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recurring expenses due within the next 7 days."""
    today = date.today()
    week_later = today + timedelta(days=7)
    
    recurring_list = db.query(RecurringExpense).options(
        joinedload(RecurringExpense.category)
    ).filter(
        RecurringExpense.user_id == current_user.id,
        RecurringExpense.is_active == True
    ).all()
    
    upcoming = []
    for rec in recurring_list:
        next_due = calculate_next_due(rec.frequency, rec.due_day)
        
        if today <= next_due <= week_later:
            days_until = (next_due - today).days
            upcoming.append(UpcomingReminder(
                id=str(rec.id),
                name=rec.name,
                amount=rec.amount,
                due_date=next_due,
                days_until=days_until,
                category={"name": rec.category.name, "icon": rec.category.icon}
            ))
    
    # Sort by days_until
    upcoming.sort(key=lambda x: x.days_until)
    
    return UpcomingReminderListResponse(upcoming=upcoming)
