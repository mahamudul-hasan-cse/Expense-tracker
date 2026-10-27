import calendar
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_user_category, get_user_income_category
from app.models.expense import Expense
from app.models.income import Income
from app.models.recurring import RecurringExpense
from app.models.user import User
from app.pagination import paginate
from app.schemas.recurring import (
    MarkPaidRequest,
    MarkPaidResponse,
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


def next_unpaid_due(
    frequency: str, due_day: int, last_paid_on: Optional[date], reference_date: Optional[date] = None
) -> date:
    """Next due date that hasn't been marked paid yet.

    last_paid_on is the due date of the cycle that was paid, so once a cycle is
    paid (even early) the next due date moves to the following cycle.
    """
    due = calculate_next_due(frequency, due_day, reference_date)
    if last_paid_on is not None and due <= last_paid_on:
        due = calculate_next_due(frequency, due_day, last_paid_on + timedelta(days=1))
    return due


def to_response(rec: RecurringExpense) -> RecurringExpenseResponse:
    return RecurringExpenseResponse(
        id=rec.id,
        kind=rec.kind,
        name=rec.name,
        amount=rec.amount,
        category=rec.category,
        income_category=rec.income_category,
        frequency=rec.frequency,
        due_day=rec.due_day,
        is_active=rec.is_active,
        last_paid_on=rec.last_paid_on,
        next_due=next_unpaid_due(rec.frequency, rec.due_day, rec.last_paid_on),
    )


def _get_owned(db: Session, recurring_id: UUID, user: User) -> RecurringExpense:
    recurring = (
        db.query(RecurringExpense)
        .options(joinedload(RecurringExpense.category), joinedload(RecurringExpense.income_category))
        .filter(RecurringExpense.id == recurring_id, RecurringExpense.user_id == user.id)
        .first()
    )
    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring expense not found")
    return recurring


@router.get("", response_model=RecurringExpenseListResponse)
def get_recurring_expenses(
    kind: Optional[str] = Query(None, pattern="^(expense|income)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recurring expenses and recurring income (optionally only one kind)."""
    query = (
        db.query(RecurringExpense)
        .options(joinedload(RecurringExpense.category), joinedload(RecurringExpense.income_category))
        .filter(RecurringExpense.user_id == current_user.id)
    )
    if kind:
        query = query.filter(RecurringExpense.kind == kind)
    query = query.order_by(RecurringExpense.created_at.desc(), RecurringExpense.id)
    recurring_list, pagination = paginate(query, page, limit)
    return RecurringExpenseListResponse(
        recurring_expenses=[to_response(r) for r in recurring_list], pagination=pagination
    )


@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_expense(
    data: RecurringExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a recurring expense (kind=expense) or recurring income (kind=income)."""
    # Verify the category exists and belongs to the user (the schema guarantees the right id is set)
    if data.category_id is not None:
        get_user_category(db, data.category_id, current_user)
    if data.income_category_id is not None:
        get_user_income_category(db, data.income_category_id, current_user)

    recurring = RecurringExpense(
        user_id=current_user.id,
        kind=data.kind,
        name=data.name,
        amount=data.amount,
        category_id=data.category_id,
        income_category_id=data.income_category_id,
        frequency=data.frequency,
        due_day=data.due_day,
    )
    db.add(recurring)
    db.commit()
    return to_response(_get_owned(db, recurring.id, current_user))


@router.put("/{recurring_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(
    recurring_id: UUID,
    data: RecurringExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing recurring expense or income."""
    recurring = _get_owned(db, recurring_id, current_user)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")

    # Required columns cannot be cleared
    for field in ("name", "amount", "category_id", "income_category_id", "frequency", "due_day", "is_active"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")

    # The category field must match the item's kind
    if recurring.kind == "expense" and "income_category_id" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recurring expenses use category_id")
    if recurring.kind == "income" and "category_id" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recurring income uses income_category_id")

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
    if data.income_category_id is not None:
        get_user_income_category(db, data.income_category_id, current_user)

    # A different schedule starts fresh: the old "paid" cycle no longer applies
    if "frequency" in update_data or "due_day" in update_data:
        recurring.last_paid_on = None

    for key, value in update_data.items():
        setattr(recurring, key, value)

    db.commit()
    return to_response(_get_owned(db, recurring_id, current_user))


@router.post("/{recurring_id}/mark-paid", response_model=MarkPaidResponse)
def mark_paid(
    recurring_id: UUID,
    data: Optional[MarkPaidRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record this cycle as paid (expense) or received (income).

    Creates the expense or income through the same validation as manual entry
    and moves next_due to the following cycle.
    """
    data = data or MarkPaidRequest()
    recurring = _get_owned(db, recurring_id, current_user)
    if not recurring.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This item is paused; resume it first")

    cycle_due = next_unpaid_due(recurring.frequency, recurring.due_day, recurring.last_paid_on)
    paid_on = data.paid_on or app_today()
    amount = data.amount or recurring.amount

    record: Expense | Income
    if recurring.kind == "expense":
        record = Expense(
            user_id=current_user.id,
            amount=amount,
            category_id=recurring.category_id,
            note=recurring.name,
            expense_date=paid_on,
        )
    else:
        record = Income(
            user_id=current_user.id,
            amount=amount,
            income_category_id=recurring.income_category_id,
            note=recurring.name,
            income_date=paid_on,
        )
    db.add(record)
    recurring.last_paid_on = cycle_due
    db.commit()

    return MarkPaidResponse(
        recurring=to_response(_get_owned(db, recurring_id, current_user)),
        record_type=recurring.kind,
        record_id=record.id,
    )


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_expense(
    recurring_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a recurring expense or income."""
    recurring = _get_owned(db, recurring_id, current_user)
    db.delete(recurring)
    db.commit()
    return None
