from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class BudgetBase(BaseModel):
    category_id: UUID
    amount: Decimal = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020, le=2100)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)


class CategoryInfo(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]

    class Config:
        from_attributes = True


class BudgetResponse(BaseModel):
    id: UUID
    category: CategoryInfo
    amount: Decimal
    month: int
    year: int
    spent: Decimal = Decimal("0")  # Calculated field
    percentage: float = 0  # Percentage of budget used
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetListResponse(BaseModel):
    budgets: list[BudgetResponse]


class BudgetSummary(BaseModel):
    total_budget: Decimal
    total_spent: Decimal
    percentage: float
    budgets: list[BudgetResponse]
