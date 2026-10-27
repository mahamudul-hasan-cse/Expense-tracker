from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.income import Income, IncomeCategory
from app.models.recurring import RecurringExpense
from app.models.user import User
from app.pagination import paginate
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.income import IncomeCategoriesListResponse

router = APIRouter(prefix="/income-categories", tags=["Income Categories"])


def _get_owned(db: Session, category_id: UUID, user: User) -> IncomeCategory:
    category = (
        db.query(IncomeCategory).filter(IncomeCategory.id == category_id, IncomeCategory.user_id == user.id).first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income category not found")
    return category


def _name_taken(db: Session, user: User, name: str, exclude_id: UUID | None = None) -> bool:
    query = db.query(IncomeCategory).filter(
        IncomeCategory.user_id == user.id, func.lower(IncomeCategory.name) == func.lower(name)
    )
    if exclude_id is not None:
        query = query.filter(IncomeCategory.id != exclude_id)
    return query.first() is not None


@router.get("", response_model=IncomeCategoriesListResponse)
def get_income_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the user's income categories (defaults first)."""
    query = (
        db.query(IncomeCategory)
        .filter(IncomeCategory.user_id == current_user.id)
        .order_by(IncomeCategory.is_default.desc(), IncomeCategory.name, IncomeCategory.id)
    )
    categories, pagination = paginate(query, page, limit)
    return IncomeCategoriesListResponse(income_categories=categories, pagination=pagination)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_income_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a user-defined income category."""
    if _name_taken(db, current_user, data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Income category with this name already exists"
        )
    category = IncomeCategory(user_id=current_user.id, name=data.name, icon=data.icon, is_default=False)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_income_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename an income category or change its icon."""
    category = _get_owned(db, category_id, current_user)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")
    if "name" in update_data:
        if update_data["name"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name cannot be null")
        if _name_taken(db, current_user, update_data["name"], exclude_id=category_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Income category with this name already exists"
            )
    for key, value in update_data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a user-defined income category that nothing uses."""
    category = _get_owned(db, category_id, current_user)
    if category.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default category")

    in_use = [
        label
        for exists, label in (
            (db.query(Income.id).filter(Income.income_category_id == category_id).first(), "income entries"),
            (
                db.query(RecurringExpense.id).filter(RecurringExpense.income_category_id == category_id).first(),
                "recurring income",
            ),
        )
        if exists
    ]
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category is used by {', '.join(in_use)}. Reassign or delete them first.",
        )
    db.delete(category)
    db.commit()
    return None
