from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from typing import Optional, Literal
from uuid import UUID
from datetime import date
import math

from app.database import get_db
from app.models.expense import Expense
from app.models.category import Category
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    PaginationInfo,
)
from app.schemas.category import CategoryResponse

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
    db: Session = Depends(get_db)
):
    """Get expenses with filtering, search, and pagination."""
    query = db.query(Expense).options(joinedload(Expense.category))
    
    # Apply filters
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if search:
        # Search in note field (case-insensitive)
        query = query.filter(Expense.note.ilike(f"%{search}%"))
    
    # Get total count
    total_items = query.count()
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
    
    # Apply sorting
    sort_mapping = {
        "date_desc": desc(Expense.expense_date),
        "date_asc": asc(Expense.expense_date),
        "amount_desc": desc(Expense.amount),
        "amount_asc": asc(Expense.amount),
    }
    query = query.order_by(sort_mapping[sort], desc(Expense.created_at))
    
    # Apply pagination
    offset = (page - 1) * limit
    expenses = query.offset(offset).limit(limit).all()
    
    return ExpenseListResponse(
        expenses=expenses,
        pagination=PaginationInfo(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense_data: ExpenseCreate, db: Session = Depends(get_db)):
    """Create a new expense."""
    # Verify category exists
    category = db.query(Category).filter(Category.id == expense_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )
    
    expense = Expense(
        amount=expense_data.amount,
        category_id=expense_data.category_id,
        note=expense_data.note,
        expense_date=expense_data.expense_date or date.today()
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    # Load category relationship
    db.refresh(expense, ["category"])
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: UUID, expense_data: ExpenseUpdate, db: Session = Depends(get_db)):
    """Update an existing expense."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Check if at least one field is provided
    update_data = expense_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided"
        )
    
    # Required columns cannot be cleared (note may be cleared with null)
    for field in ("amount", "category_id", "expense_date"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null"
            )

    # Verify category if being updated
    if expense_data.category_id is not None:
        category = db.query(Category).filter(Category.id == expense_data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Update fields
    for key, value in update_data.items():
        setattr(expense, key, value)
    
    db.commit()
    db.refresh(expense, ["category"])
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: UUID, db: Session = Depends(get_db)):
    """Delete an expense."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    db.delete(expense)
    db.commit()
    return None
