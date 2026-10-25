from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Optional, Literal, Annotated
from app.schemas.category import CategoryResponse
from app.schemas.types import Money, MoneyIn


class RecurringExpenseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    amount: MoneyIn
    category_id: UUID
    frequency: Literal["weekly", "monthly"]
    due_day: int = Field(..., ge=1, le=31)

    @field_validator("due_day")
    @classmethod
    def validate_due_day(cls, v, info):
        frequency = info.data.get("frequency")
        if frequency == "weekly" and (v < 1 or v > 7):
            raise ValueError("For weekly frequency, due_day must be 1-7 (1=Monday)")
        return v


class RecurringExpenseCreate(RecurringExpenseBase):
    pass


class RecurringExpenseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[MoneyIn] = None
    category_id: Optional[UUID] = None
    frequency: Optional[Literal["weekly", "monthly"]] = None
    due_day: Optional[int] = Field(None, ge=1, le=31)
    is_active: Optional[bool] = None


class RecurringExpenseResponse(BaseModel):
    id: UUID
    name: str
    amount: Money
    category: CategoryResponse
    frequency: str
    due_day: int
    is_active: bool
    next_due: date

    class Config:
        from_attributes = True


class RecurringExpenseListResponse(BaseModel):
    recurring_expenses: list[RecurringExpenseResponse]
