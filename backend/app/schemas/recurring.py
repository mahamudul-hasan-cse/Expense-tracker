from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.category import CategoryResponse
from app.schemas.pagination import PaginationInfo
from app.schemas.types import Money, MoneyIn
from app.timeutil import today as app_today


class RecurringExpenseBase(BaseModel):
    # "expense" = a bill, "income" = e.g. a monthly salary
    kind: Literal["expense", "income"] = "expense"
    name: str = Field(..., min_length=1, max_length=200)
    amount: MoneyIn
    category_id: Optional[UUID] = None
    income_category_id: Optional[UUID] = None
    frequency: Literal["weekly", "monthly"]
    due_day: int = Field(..., ge=1, le=31)

    @field_validator("due_day")
    @classmethod
    def validate_due_day(cls, v, info):
        frequency = info.data.get("frequency")
        if frequency == "weekly" and (v < 1 or v > 7):
            raise ValueError("For weekly frequency, due_day must be 1-7 (1=Monday)")
        return v

    @model_validator(mode="after")
    def category_matches_kind(self):
        if self.kind == "expense" and (self.category_id is None or self.income_category_id is not None):
            raise ValueError("Recurring expenses need category_id (and no income_category_id)")
        if self.kind == "income" and (self.income_category_id is None or self.category_id is not None):
            raise ValueError("Recurring income needs income_category_id (and no category_id)")
        return self


class RecurringExpenseCreate(RecurringExpenseBase):
    pass


class RecurringExpenseUpdate(BaseModel):
    # kind can't change after creation; delete and recreate instead
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[MoneyIn] = None
    category_id: Optional[UUID] = None
    income_category_id: Optional[UUID] = None
    frequency: Optional[Literal["weekly", "monthly"]] = None
    due_day: Optional[int] = Field(None, ge=1, le=31)
    is_active: Optional[bool] = None


class RecurringExpenseResponse(BaseModel):
    id: UUID
    kind: Literal["expense", "income"]
    name: str
    amount: Money
    category: Optional[CategoryResponse]
    income_category: Optional[CategoryResponse]
    frequency: str
    due_day: int
    is_active: bool
    last_paid_on: Optional[date]
    next_due: date

    class Config:
        from_attributes = True


class RecurringExpenseListResponse(BaseModel):
    recurring_expenses: list[RecurringExpenseResponse]
    pagination: PaginationInfo


class MarkPaidRequest(BaseModel):
    # When the money actually moved (default: today, Asia/Dhaka)
    paid_on: Optional[date] = None
    # Defaults to the recurring amount (e.g. a bill that was a bit higher this month)
    amount: Optional[MoneyIn] = None

    @field_validator("paid_on")
    @classmethod
    def not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > app_today():
            raise ValueError("Date cannot be in the future")
        return v


class MarkPaidResponse(BaseModel):
    recurring: RecurringExpenseResponse
    record_type: Literal["expense", "income"]
    record_id: UUID
