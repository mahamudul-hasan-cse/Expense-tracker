from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import Optional
from uuid import UUID
from datetime import date
from decimal import Decimal

from app.database import get_db
from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetListResponse,
    BudgetSummary,
    CategoryInfo,
)

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def calculate_spent(db: Session, category_id: UUID, month: int, year: int) -> Decimal:
    """Calculate total spent for a category in a given month/year."""
    result = db.query(func.sum(Expense.amount)).filter(
        Expense.category_id == category_id,
        extract("month", Expense.expense_date) == month,
        extract("year", Expense.expense_date) == year,
    ).scalar()
    return Decimal(result) if result else Decimal("0")


@router.get("", response_model=BudgetListResponse)
def get_budgets(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db)
):
    """Get budgets for a specific month/year. Defaults to current month."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    budgets = db.query(Budget).options(
        joinedload(Budget.category)
    ).filter(
        Budget.month == target_month,
        Budget.year == target_year
    ).all()

    result = []
    for budget in budgets:
        spent = calculate_spent(db, budget.category_id, target_month, target_year)
        percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0
        result.append(BudgetResponse(
            id=budget.id,
            category=CategoryInfo(
                id=budget.category.id,
                name=budget.category.name,
                icon=budget.category.icon
            ),
            amount=budget.amount,
            month=budget.month,
            year=budget.year,
            spent=spent,
            percentage=round(percentage, 1),
            created_at=budget.created_at
        ))

    return BudgetListResponse(budgets=result)


@router.get("/summary", response_model=BudgetSummary)
def get_budget_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db)
):
    """Get budget summary for a specific month/year."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    budgets = db.query(Budget).options(
        joinedload(Budget.category)
    ).filter(
        Budget.month == target_month,
        Budget.year == target_year
    ).all()

    result = []
    total_budget = Decimal("0")
    total_spent = Decimal("0")

    for budget in budgets:
        spent = calculate_spent(db, budget.category_id, target_month, target_year)
        percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0
        total_budget += budget.amount
        total_spent += spent
        result.append(BudgetResponse(
            id=budget.id,
            category=CategoryInfo(
                id=budget.category.id,
                name=budget.category.name,
                icon=budget.category.icon
            ),
            amount=budget.amount,
            month=budget.month,
            year=budget.year,
            spent=spent,
            percentage=round(percentage, 1),
            created_at=budget.created_at
        ))

    overall_percentage = float(total_spent / total_budget * 100) if total_budget > 0 else 0

    return BudgetSummary(
        total_budget=total_budget,
        total_spent=total_spent,
        percentage=round(overall_percentage, 1),
        budgets=result
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(budget_data: BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget for a category/month/year."""
    # Verify category exists
    category = db.query(Category).filter(Category.id == budget_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    # Check if budget already exists for this category/month/year
    existing = db.query(Budget).filter(
        Budget.category_id == budget_data.category_id,
        Budget.month == budget_data.month,
        Budget.year == budget_data.year
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category/month/year. Use PUT to update."
        )

    budget = Budget(
        category_id=budget_data.category_id,
        amount=budget_data.amount,
        month=budget_data.month,
        year=budget_data.year
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    spent = calculate_spent(db, budget.category_id, budget.month, budget.year)
    percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0

    return BudgetResponse(
        id=budget.id,
        category=CategoryInfo(
            id=category.id,
            name=category.name,
            icon=category.icon
        ),
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        spent=spent,
        percentage=round(percentage, 1),
        created_at=budget.created_at
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(budget_id: UUID, budget_data: BudgetUpdate, db: Session = Depends(get_db)):
    """Update budget amount."""
    budget = db.query(Budget).options(
        joinedload(Budget.category)
    ).filter(Budget.id == budget_id).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    if budget_data.amount is not None:
        budget.amount = budget_data.amount

    db.commit()
    db.refresh(budget)

    spent = calculate_spent(db, budget.category_id, budget.month, budget.year)
    percentage = float(spent / budget.amount * 100) if budget.amount > 0 else 0

    return BudgetResponse(
        id=budget.id,
        category=CategoryInfo(
            id=budget.category.id,
            name=budget.category.name,
            icon=budget.category.icon
        ),
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        spent=spent,
        percentage=round(percentage, 1),
        created_at=budget.created_at
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: UUID, db: Session = Depends(get_db)):
    """Delete a budget."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    db.delete(budget)
    db.commit()
    return None
