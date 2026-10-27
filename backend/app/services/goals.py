"""Savings-goal progress. Shared by the API and (later) the assistant's tools."""

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_UP, Decimal
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.goal import GoalContribution, SavingsGoal
from app.timeutil import app_timezone
from app.timeutil import today as app_today

DAYS_PER_MONTH = 30.4375  # average Gregorian month


@dataclass(frozen=True)
class GoalProgress:
    saved: Decimal
    remaining: Decimal
    progress_pct: float  # raw, may exceed 100
    state: str  # completed | no_deadline | overdue | on_track | behind
    on_track: Optional[bool]
    months_left: Optional[int]
    required_per_month: Optional[Decimal]


def saved_by_goal(db: Session, goal_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
    """Sum of contributions per goal, in one query."""
    ids = list(goal_ids)
    if not ids:
        return {}
    rows = (
        db.query(GoalContribution.goal_id, func.sum(GoalContribution.amount))
        .filter(GoalContribution.goal_id.in_(ids))
        .group_by(GoalContribution.goal_id)
        .all()
    )
    return {goal_id: Decimal(total) for goal_id, total in rows}


def compute_progress(goal: SavingsGoal, saved: Decimal, today: Optional[date] = None) -> GoalProgress:
    today = today or app_today()
    target = goal.target_amount
    remaining = max(target - saved, Decimal("0"))
    progress_pct = round(float(saved / target * 100), 1) if target > 0 else 0.0

    if saved >= target:
        return GoalProgress(saved, Decimal("0"), progress_pct, "completed", True, None, Decimal("0"))

    if goal.target_date is None:
        return GoalProgress(saved, remaining, progress_pct, "no_deadline", None, None, None)

    if goal.target_date < today:
        # Deadline passed: everything that's left is due now
        return GoalProgress(saved, remaining, progress_pct, "overdue", False, 0, remaining)

    days_left = (goal.target_date - today).days
    months_left = max(1, math.ceil(days_left / DAYS_PER_MONTH))
    required = (remaining / months_left).quantize(Decimal("0.01"), rounding=ROUND_UP)

    # On track = saved at least the target pro-rated over the time elapsed since creation
    created = goal.created_at.astimezone(app_timezone()).date()
    total_days = max((goal.target_date - created).days, 1)
    elapsed_days = min(max((today - created).days, 0), total_days)
    expected = target * Decimal(elapsed_days) / Decimal(total_days)
    on_track = saved >= expected
    return GoalProgress(
        saved, remaining, progress_pct, "on_track" if on_track else "behind", on_track, months_left, required
    )
