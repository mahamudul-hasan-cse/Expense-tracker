from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_user_category
from app.models.budget import Budget
from app.models.expense import Expense
from app.models.user import User
from app.pagination import paginate
from app.schemas.budget import (
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetSummary,
    BudgetUpdate,
    CategoryInfo,
)
from app.timeutil import today as app_today

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def _month_range(month: int, year: int) -> tuple[date, date]:
    """First day of the month and first day of the next month (exclusive end)."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def spent_by_category(db: Session, user_id: UUID, month: int, year: int) -> dict[UUID, Decimal]:
    """Total spent per category for a user's month, in one grouped query."""
    start, end = _month_range(month, year)
    rows = (
        db.query(Expense.category_id, func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            # A date range (not extract()) so ix_expenses_user_date can be used
            Expense.expense_date >= start,
            Expense.expense_date < end,
        )
        .group_by(Expense.category_id)
        .all()
    )
    return {category_id: Decimal(total) for category_id, total in rows}


def calculate_spent(db: Session, user_id: UUID, category_id: UUID, month: int, year: int) -> Decimal:
    """Calculate total spent by a user for a category in a given month/year."""
    start, end = _month_range(month, year)
    result = (
        db.query(func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            Expense.expense_date >= start,
            Expense.expense_date < end,
        )
        .scalar()
    )
    return Decimal(result) if result else Decimal("0")


def _to_response(budget: Budget, spent: Decimal) -> BudgetResponse:
    percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0
    return BudgetResponse(
        id=budget.id,
        category=CategoryInfo(id=budget.category.id, name=budget.category.name, icon=budget.category.icon),
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        spent=spent,
        percentage=round(percentage, 1),
        created_at=budget.created_at,
    )


def _budgets_query(db: Session, user_id: UUID, month: int, year: int):
    return (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
        .order_by(Budget.created_at, Budget.id)
    )


@router.get("", response_model=BudgetListResponse)
def get_budgets(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get budgets for a specific month/year. Defaults to current month."""
    today = app_today()
    target_month = month or today.month
    target_year = year or today.year

    budgets, pagination = paginate(_budgets_query(db, current_user.id, target_month, target_year), page, limit)
    spent = spent_by_category(db, current_user.id, target_month, target_year)

    return BudgetListResponse(
        budgets=[_to_response(b, spent.get(b.category_id, Decimal("0"))) for b in budgets],
        pagination=pagination,
    )


@router.get("/summary", response_model=BudgetSummary)
def get_budget_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get budget summary for a specific month/year.

    Not paginated: totals must cover every budget, and there is at most one
    budget per category per month.
    """
    today = app_today()
    target_month = month or today.month
    target_year = year or today.year

    budgets = _budgets_query(db, current_user.id, target_month, target_year).all()
    spent = spent_by_category(db, current_user.id, target_month, target_year)
    result = [_to_response(b, spent.get(b.category_id, Decimal("0"))) for b in budgets]

    total_budget = sum((b.amount for b in budgets), Decimal("0"))
    total_spent = sum((r.spent for r in result), Decimal("0"))
    overall_percentage = float(total_spent / total_budget * 100) if total_budget > 0 else 0

    return BudgetSummary(
        total_budget=total_budget, total_spent=total_spent, percentage=round(overall_percentage, 1), budgets=result
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new budget for a category/month/year."""
    # Verify category exists and belongs to the user
    get_user_category(db, budget_data.category_id, current_user)

    # Check if budget already exists for this category/month/year
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category_id == budget_data.category_id,
            Budget.month == budget_data.month,
            Budget.year == budget_data.year,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category/month/year. Use PUT to update.",
        )

    budget = Budget(
        user_id=current_user.id,
        category_id=budget_data.category_id,
        amount=budget_data.amount,
        month=budget_data.month,
        year=budget_data.year,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    spent = calculate_spent(db, current_user.id, budget.category_id, budget.month, budget.year)
    return _to_response(budget, spent)


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update budget amount."""
    budget = (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )

    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    if budget_data.amount is not None:
        budget.amount = budget_data.amount

    db.commit()
    db.refresh(budget)

    spent = calculate_spent(db, current_user.id, budget.category_id, budget.month, budget.year)
    return _to_response(budget, spent)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a budget."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()

    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    db.delete(budget)
    db.commit()
    return None
