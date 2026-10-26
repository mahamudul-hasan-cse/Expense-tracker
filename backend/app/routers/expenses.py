from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import UnaryExpression, asc, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_user_category
from app.models.expense import Expense
from app.models.user import User
from app.pagination import paginate
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
)
from app.timeutil import today as app_today

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=ExpenseListResponse)
def get_expenses(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    category_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = "date_desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get expenses with filtering, search, and pagination."""
    query = db.query(Expense).options(joinedload(Expense.category)).filter(Expense.user_id == current_user.id)

    # Apply filters
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if search:
        # Search in note field (case-insensitive)
        # Escape LIKE wildcards so they match literally
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(Expense.note.ilike(f"%{escaped}%", escape="\\"))

    # Apply sorting
    sort_mapping: dict[str, UnaryExpression] = {
        "date_desc": desc(Expense.expense_date),
        "date_asc": asc(Expense.expense_date),
        "amount_desc": desc(Expense.amount),
        "amount_asc": asc(Expense.amount),
    }
    query = query.order_by(sort_mapping[sort], desc(Expense.created_at), Expense.id)

    expenses, pagination = paginate(query, page, limit)
    return ExpenseListResponse(expenses=expenses, pagination=pagination)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new expense."""
    # Verify category exists and belongs to the user
    get_user_category(db, expense_data.category_id, current_user)

    expense = Expense(
        user_id=current_user.id,
        amount=expense_data.amount,
        category_id=expense_data.category_id,
        note=expense_data.note,
        expense_date=expense_data.expense_date or app_today(),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Load category relationship
    db.refresh(expense, ["category"])
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    expense_data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing expense."""
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == current_user.id).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Check if at least one field is provided
    update_data = expense_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")

    # Required columns cannot be cleared (note may be cleared with null)
    for field in ("amount", "category_id", "expense_date"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")

    # Verify category if being updated
    if expense_data.category_id is not None:
        get_user_category(db, expense_data.category_id, current_user)

    # Update fields
    for key, value in update_data.items():
        setattr(expense, key, value)

    db.commit()
    db.refresh(expense, ["category"])
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an expense."""
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == current_user.id).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return None
