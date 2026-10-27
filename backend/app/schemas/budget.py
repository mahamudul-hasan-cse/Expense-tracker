from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginationInfo
from app.schemas.types import Money, MoneyIn


class BudgetBase(BaseModel):
    category_id: UUID
    amount: MoneyIn
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020, le=2100)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[MoneyIn] = None


class CategoryInfo(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BudgetResponse(BaseModel):
    id: UUID
    category: CategoryInfo
    amount: Money
    month: int
    year: int
    spent: Money = Decimal("0")  # Calculated field
    percentage: float = 0  # Percentage of budget used
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetListResponse(BaseModel):
    budgets: list[BudgetResponse]
    pagination: PaginationInfo


class BudgetSummary(BaseModel):
    total_budget: Money
    total_spent: Money
    percentage: float
    budgets: list[BudgetResponse]
