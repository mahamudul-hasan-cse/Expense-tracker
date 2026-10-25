from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.recurring import RecurringExpense
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoriesListResponse,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=CategoriesListResponse)
def get_categories(db: Session = Depends(get_db)):
    """Get all categories."""
    categories = db.query(Category).order_by(Category.is_default.desc(), Category.name).all()
    return CategoriesListResponse(categories=categories)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category_data: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category."""
    # Check for existing category (case-insensitive)
    existing = db.query(Category).filter(
        func.lower(Category.name) == func.lower(category_data.name)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = Category(
        name=category_data.name,
        icon=category_data.icon,
        is_default=False
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: UUID, category_data: CategoryUpdate, db: Session = Depends(get_db)):
    """Rename a category or change its icon."""
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    update_data = category_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided"
        )
    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name cannot be null"
        )

    # Check for another category with the same name (case-insensitive)
    if "name" in update_data:
        existing = db.query(Category).filter(
            func.lower(Category.name) == func.lower(update_data["name"]),
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )

    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: Session = Depends(get_db)):
    """Delete a category (non-default only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    if category.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default category"
        )

    # Refuse to delete categories still referenced by other records
    in_use = [
        label
        for model, label in (
            (Expense, "expenses"),
            (RecurringExpense, "recurring expenses"),
            (Budget, "budgets"),
        )
        if db.query(model.id).filter(model.category_id == category_id).first()
    ]
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category is used by {', '.join(in_use)}. Reassign or delete them first."
        )
    
    db.delete(category)
    db.commit()
    return None
