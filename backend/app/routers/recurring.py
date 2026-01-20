from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from uuid import UUID
from datetime import date, timedelta
import calendar

from app.database import get_db
from app.models.recurring import RecurringExpense
from app.models.category import Category
from app.schemas.recurring import (
    RecurringExpenseCreate,
    RecurringExpenseUpdate,
    RecurringExpenseResponse,
    RecurringExpenseListResponse,
)

router = APIRouter(prefix="/recurring", tags=["Recurring Expenses"])


def calculate_next_due(frequency: str, due_day: int, reference_date: date = None) -> date:
    """Calculate the next due date based on frequency and due_day."""
    today = reference_date or date.today()
    
    if frequency == "weekly":
        # due_day: 1=Monday, 7=Sunday
        current_weekday = today.weekday() + 1  # Python weekday: 0=Monday
        days_until = (due_day - current_weekday) % 7
        if days_until == 0 and today == reference_date:
            days_until = 7
        next_due = today + timedelta(days=days_until if days_until > 0 else 7)
    else:  # monthly
        year = today.year
        month = today.month
        
        # Get the last day of the current month
        _, last_day = calendar.monthrange(year, month)
        actual_due_day = min(due_day, last_day)
        
        if today.day < actual_due_day:
            next_due = date(year, month, actual_due_day)
        else:
            # Move to next month
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            _, next_last_day = calendar.monthrange(next_year, next_month)
            next_due = date(next_year, next_month, min(due_day, next_last_day))
    
    return next_due


@router.get("", response_model=RecurringExpenseListResponse)
def get_recurring_expenses(db: Session = Depends(get_db)):
    """Get all recurring expenses."""
    recurring_list = db.query(RecurringExpense).options(
        joinedload(RecurringExpense.category)
    ).order_by(RecurringExpense.created_at.desc()).all()
    
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
            "next_due": calculate_next_due(rec.frequency, rec.due_day)
        }
        result.append(rec_dict)
    
    return RecurringExpenseListResponse(recurring_expenses=result)


@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_expense(data: RecurringExpenseCreate, db: Session = Depends(get_db)):
    """Create a new recurring expense."""
    # Verify category exists
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )
    
    recurring = RecurringExpense(
        name=data.name,
        amount=data.amount,
        category_id=data.category_id,
        frequency=data.frequency,
        due_day=data.due_day
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
        next_due=calculate_next_due(recurring.frequency, recurring.due_day)
    )


@router.put("/{recurring_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(recurring_id: UUID, data: RecurringExpenseUpdate, db: Session = Depends(get_db)):
    """Update an existing recurring expense."""
    recurring = db.query(RecurringExpense).filter(RecurringExpense.id == recurring_id).first()
    
    if not recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense not found"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Verify category if being updated
    if data.category_id is not None:
        category = db.query(Category).filter(Category.id == data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
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
        next_due=calculate_next_due(recurring.frequency, recurring.due_day)
    )


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_expense(recurring_id: UUID, db: Session = Depends(get_db)):
    """Delete a recurring expense."""
    recurring = db.query(RecurringExpense).filter(RecurringExpense.id == recurring_id).first()
    
    if not recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense not found"
        )
    
    db.delete(recurring)
    db.commit()
    return None
