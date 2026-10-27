from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.category import CategoryResponse
from app.schemas.pagination import PaginationInfo
from app.schemas.types import Money, MoneyIn
from app.timeutil import today as app_today


def _not_future(v: Optional[date]) -> Optional[date]:
    if v is not None and v > app_today():
        raise ValueError("Income date cannot be in the future")
    return v


class IncomeCategoriesListResponse(BaseModel):
    income_categories: list[CategoryResponse]
    pagination: PaginationInfo


class IncomeCreate(BaseModel):
    amount: MoneyIn
    income_category_id: UUID
    note: Optional[str] = Field(None, max_length=500)
    income_date: Optional[date] = None

    _check_date = field_validator("income_date")(_not_future)


class IncomeUpdate(BaseModel):
    amount: Optional[MoneyIn] = None
    income_category_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=500)
    income_date: Optional[date] = None

    _check_date = field_validator("income_date")(_not_future)


class IncomeResponse(BaseModel):
    id: UUID
    amount: Money
    category: CategoryResponse
    note: Optional[str]
    income_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncomeListResponse(BaseModel):
    incomes: list[IncomeResponse]
    pagination: PaginationInfo
