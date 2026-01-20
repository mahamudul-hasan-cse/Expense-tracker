from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.category import Category
from app.schemas.category import (
    CategoryCreate,
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
    
    db.delete(category)
    db.commit()
    return None
