from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import UnaryExpression, asc, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_user_income_category
from app.models.income import Income
from app.models.user import User
from app.pagination import paginate
from app.schemas.income import IncomeCreate, IncomeListResponse, IncomeResponse, IncomeUpdate
from app.timeutil import today as app_today

router = APIRouter(prefix="/incomes", tags=["Income"])


def _get_owned(db: Session, income_id: UUID, user: User) -> Income:
    income = (
        db.query(Income)
        .options(joinedload(Income.category))
        .filter(Income.id == income_id, Income.user_id == user.id)
        .first()
    )
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income not found")
    return income


@router.get("", response_model=IncomeListResponse)
def get_incomes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    income_category_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = "date_desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List income with filtering, search and pagination (same options as expenses)."""
    query = db.query(Income).options(joinedload(Income.category)).filter(Income.user_id == current_user.id)
    if income_category_id:
        query = query.filter(Income.income_category_id == income_category_id)
    if start_date:
        query = query.filter(Income.income_date >= start_date)
    if end_date:
        query = query.filter(Income.income_date <= end_date)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(Income.note.ilike(f"%{escaped}%", escape="\\"))

    sort_mapping: dict[str, UnaryExpression] = {
        "date_desc": desc(Income.income_date),
        "date_asc": asc(Income.income_date),
        "amount_desc": desc(Income.amount),
        "amount_asc": asc(Income.amount),
    }
    query = query.order_by(sort_mapping[sort], desc(Income.created_at), Income.id)
    incomes, pagination = paginate(query, page, limit)
    return IncomeListResponse(incomes=incomes, pagination=pagination)


@router.post("", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
def create_income(
    data: IncomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record money received."""
    get_user_income_category(db, data.income_category_id, current_user)
    income = Income(
        user_id=current_user.id,
        amount=data.amount,
        income_category_id=data.income_category_id,
        note=data.note,
        income_date=data.income_date or app_today(),
    )
    db.add(income)
    db.commit()
    return _get_owned(db, income.id, current_user)


@router.put("/{income_id}", response_model=IncomeResponse)
def update_income(
    income_id: UUID,
    data: IncomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income = _get_owned(db, income_id, current_user)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")
    # Required columns cannot be cleared (note may be cleared with null)
    for field in ("amount", "income_category_id", "income_date"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")
    if data.income_category_id is not None:
        get_user_income_category(db, data.income_category_id, current_user)
    for key, value in update_data.items():
        setattr(income, key, value)
    db.commit()
    return _get_owned(db, income_id, current_user)


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    income_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    income = _get_owned(db, income_id, current_user)
    db.delete(income)
    db.commit()
    return None
