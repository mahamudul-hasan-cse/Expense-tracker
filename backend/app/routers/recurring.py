import calendar
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_user_category
from app.models.recurring import RecurringExpense
from app.models.user import User
from app.pagination import paginate
from app.schemas.recurring import (
    RecurringExpenseCreate,
    RecurringExpenseListResponse,
    RecurringExpenseResponse,
    RecurringExpenseUpdate,
)
from app.timeutil import today as app_today

router = APIRouter(prefix="/recurring", tags=["Recurring Expenses"])


def calculate_next_due(frequency: str, due_day: int, reference_date: Optional[date] = None) -> date:
    """Calculate the next due date (today counts as due) based on frequency and due_day."""
    today = reference_date or app_today()

    if frequency == "weekly":
        # due_day: 1=Monday, 7=Sunday; Python weekday: 0=Monday
        days_until = (due_day - (today.weekday() + 1)) % 7
        return today + timedelta(days=days_until)

    # monthly: clamp due_day to the month's length (e.g. 31 -> 28/29 in February)
    _, last_day = calendar.monthrange(today.year, today.month)
    if today.day <= min(due_day, last_day):
        return date(today.year, today.month, min(due_day, last_day))

    next_year, next_month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    _, next_last_day = calendar.monthrange(next_year, next_month)
    return date(next_year, next_month, min(due_day, next_last_day))


@router.get("", response_model=RecurringExpenseListResponse)
def get_recurring_expenses(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all recurring expenses."""
    query = (
        db.query(RecurringExpense)
        .options(joinedload(RecurringExpense.category))
        .filter(RecurringExpense.user_id == current_user.id)
        .order_by(RecurringExpense.created_at.desc(), RecurringExpense.id)
    )
    recurring_list, pagination = paginate(query, page, limit)

    # Add next_due to each item
    result = []
    for rec in recurring_list:
        rec_dict = {
            "id": rec.id,
            "name": rec.name,
            "amount": rec.amount,
            "category": rec.category,
            "frequency": rec.frequency,
            "due_day": rec.due_day,
            "is_active": rec.is_active,
            "next_due": calculate_next_due(rec.frequency, rec.due_day),
        }
        result.append(rec_dict)

    return RecurringExpenseListResponse(recurring_expenses=result, pagination=pagination)


@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_expense(
    data: RecurringExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new recurring expense."""
    # Verify category exists and belongs to the user
    get_user_category(db, data.category_id, current_user)

    recurring = RecurringExpense(
        user_id=current_user.id,
        name=data.name,
        amount=data.amount,
        category_id=data.category_id,
        frequency=data.frequency,
        due_day=data.due_day,
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring, ["category"])

    # Return with calculated next_due
    return RecurringExpenseResponse(
        id=recurring.id,
        name=recurring.name,
        amount=recurring.amount,
        category=recurring.category,
        frequency=recurring.frequency,
        due_day=recurring.due_day,
        is_active=recurring.is_active,
        next_due=calculate_next_due(recurring.frequency, recurring.due_day),
    )


@router.put("/{recurring_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(
    recurring_id: UUID,
    data: RecurringExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing recurring expense."""
    recurring = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.id == recurring_id, RecurringExpense.user_id == current_user.id)
        .first()
    )

    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring expense not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")

    # Required columns cannot be cleared
    for field in ("name", "amount", "category_id", "frequency", "due_day", "is_active"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")

    # Validate due_day against the resulting frequency
    frequency = update_data.get("frequency", recurring.frequency)
    due_day = update_data.get("due_day", recurring.due_day)
    if frequency == "weekly" and not 1 <= due_day <= 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="For weekly frequency, due_day must be 1-7 (1=Monday)"
        )

    # Verify category if being updated
    if data.category_id is not None:
        get_user_category(db, data.category_id, current_user)

    for key, value in update_data.items():
        setattr(recurring, key, value)

    db.commit()
    db.refresh(recurring, ["category"])

    return RecurringExpenseResponse(
        id=recurring.id,
        name=recurring.name,
        amount=recurring.amount,
        category=recurring.category,
        frequency=recurring.frequency,
        due_day=recurring.due_day,
        is_active=recurring.is_active,
        next_due=calculate_next_due(recurring.frequency, recurring.due_day),
    )


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_expense(
    recurring_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a recurring expense."""
    recurring = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.id == recurring_id, RecurringExpense.user_id == current_user.id)
        .first()
    )

    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring expense not found")

    db.delete(recurring)
    db.commit()
    return None
