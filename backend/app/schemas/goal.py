from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.pagination import PaginationInfo
from app.schemas.types import Money, MoneyIn
from app.timeutil import today as app_today

GoalState = Literal["completed", "no_deadline", "overdue", "on_track", "behind"]

# Contribution amounts: non-zero, 2 decimals, within NUMERIC(12, 2). Negative = withdrawal.
SignedMoneyIn = Annotated[Decimal, Field(ge=Decimal("-99999999.99"), le=Decimal("99999999.99"), decimal_places=2)]


def _strip_name(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("Name cannot be blank")
    return v


def _future_deadline(v: Optional[date]) -> Optional[date]:
    if v is not None and v <= app_today():
        raise ValueError("Deadline must be in the future")
    return v


class GoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    target_amount: MoneyIn
    target_date: Optional[date] = None

    _name = field_validator("name")(_strip_name)
    _deadline = field_validator("target_date")(_future_deadline)


class GoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    target_amount: Optional[MoneyIn] = None
    # Send null to remove the deadline
    target_date: Optional[date] = None
    status: Optional[Literal["active", "archived"]] = None

    _name = field_validator("name")(_strip_name)
    _deadline = field_validator("target_date")(_future_deadline)


class GoalResponse(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]
    target_amount: Money
    target_date: Optional[date]
    status: Literal["active", "archived"]
    created_at: datetime
    # Computed progress (app/services/goals.py)
    saved: Money
    remaining: Money
    progress_pct: float
    state: GoalState
    on_track: Optional[bool]
    months_left: Optional[int]
    required_per_month: Optional[Money]


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    pagination: PaginationInfo


class ContributionCreate(BaseModel):
    amount: SignedMoneyIn
    contributed_on: Optional[date] = None
    note: Optional[str] = Field(None, max_length=200)

    @field_validator("amount")
    @classmethod
    def non_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v

    @field_validator("contributed_on")
    @classmethod
    def not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > app_today():
            raise ValueError("Date cannot be in the future")
        return v


class ContributionResponse(BaseModel):
    id: UUID
    goal_id: UUID
    amount: Money
    contributed_on: date
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ContributionListResponse(BaseModel):
    contributions: list[ContributionResponse]
    pagination: PaginationInfo
