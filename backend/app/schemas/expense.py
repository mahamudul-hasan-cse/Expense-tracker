from pydantic import BaseModel, Field, field_validator, condecimal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Annotated
from app.schemas.category import CategoryResponse
from app.schemas.types import Money, MoneyIn
from app.schemas.pagination import PaginationInfo


class ExpenseBase(BaseModel):
    amount: MoneyIn
    category_id: UUID
    note: Optional[str] = Field(None, max_length=500)
    expense_date: Optional[date] = None

    @field_validator("expense_date")
    @classmethod
    def validate_expense_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Expense date cannot be in the future")
        return v


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Optional[MoneyIn] = None
    category_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=500)
    expense_date: Optional[date] = None

    @field_validator("expense_date")
    @classmethod
    def validate_expense_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Expense date cannot be in the future")
        return v


class ExpenseResponse(BaseModel):
    id: UUID
    amount: Money
    category: CategoryResponse
    note: Optional[str]
    expense_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    expenses: list[ExpenseResponse]
    pagination: PaginationInfo
