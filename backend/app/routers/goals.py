from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.goal import GoalContribution, SavingsGoal
from app.models.user import User
from app.pagination import paginate
from app.schemas.goal import (
    ContributionCreate,
    ContributionListResponse,
    GoalCreate,
    GoalListResponse,
    GoalResponse,
    GoalUpdate,
)
from app.services.goals import compute_progress, saved_by_goal
from app.timeutil import today as app_today

router = APIRouter(prefix="/goals", tags=["Savings Goals"])


def to_response(goal: SavingsGoal, saved: Decimal) -> GoalResponse:
    progress = compute_progress(goal, saved)
    return GoalResponse(
        id=goal.id,
        name=goal.name,
        icon=goal.icon,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        status=goal.status,
        created_at=goal.created_at,
        saved=progress.saved,
        remaining=progress.remaining,
        progress_pct=progress.progress_pct,
        state=progress.state,
        on_track=progress.on_track,
        months_left=progress.months_left,
        required_per_month=progress.required_per_month,
    )


def _get_owned(db: Session, goal_id: UUID, user: User) -> SavingsGoal:
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == user.id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def _saved(db: Session, goal: SavingsGoal) -> Decimal:
    return saved_by_goal(db, [goal.id]).get(goal.id, Decimal("0"))


def _name_taken(db: Session, user: User, name: str, exclude_id: UUID | None = None) -> bool:
    query = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user.id, func.lower(SavingsGoal.name) == func.lower(name)
    )
    if exclude_id is not None:
        query = query.filter(SavingsGoal.id != exclude_id)
    return query.first() is not None


@router.get("", response_model=GoalListResponse)
def get_goals(
    status_filter: Literal["active", "archived", "all"] = Query("all", alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List goals with computed progress (active first, then by deadline)."""
    query = db.query(SavingsGoal).filter(SavingsGoal.user_id == current_user.id)
    if status_filter != "all":
        query = query.filter(SavingsGoal.status == status_filter)
    query = query.order_by(
        SavingsGoal.status, SavingsGoal.target_date.asc().nulls_last(), SavingsGoal.created_at, SavingsGoal.id
    )
    goals, pagination = paginate(query, page, limit)
    saved = saved_by_goal(db, [g.id for g in goals])
    return GoalListResponse(goals=[to_response(g, saved.get(g.id, Decimal("0"))) for g in goals], pagination=pagination)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    data: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if _name_taken(db, current_user, data.name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A goal with this name already exists")
    goal = SavingsGoal(
        user_id=current_user.id,
        name=data.name,
        icon=data.icon,
        target_amount=data.target_amount,
        target_date=data.target_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return to_response(goal, Decimal("0"))


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: UUID,
    data: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a goal, remove its deadline (target_date: null), or archive/unarchive it."""
    goal = _get_owned(db, goal_id, current_user)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")
    for field in ("name", "target_amount", "status"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be null")
    if "name" in update_data and _name_taken(db, current_user, update_data["name"], exclude_id=goal_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A goal with this name already exists")
    for key, value in update_data.items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return to_response(goal, _saved(db, goal))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a goal and its contributions.

    Contributions are only earmarks, so income, expenses and Saved don't change.
    """
    goal = _get_owned(db, goal_id, current_user)
    db.delete(goal)  # contributions cascade in the database
    db.commit()
    return None


# --- Contributions -----------------------------------------------------------


@router.get("/{goal_id}/contributions", response_model=ContributionListResponse)
def get_contributions(
    goal_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned(db, goal_id, current_user)
    query = (
        db.query(GoalContribution)
        .filter(GoalContribution.goal_id == goal_id, GoalContribution.user_id == current_user.id)
        .order_by(GoalContribution.contributed_on.desc(), GoalContribution.created_at.desc(), GoalContribution.id)
    )
    contributions, pagination = paginate(query, page, limit)
    return ContributionListResponse(contributions=contributions, pagination=pagination)


@router.post("/{goal_id}/contributions", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def add_contribution(
    goal_id: UUID,
    data: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Put money toward a goal (positive) or take it back (negative). Returns the updated goal."""
    goal = _get_owned(db, goal_id, current_user)
    if goal.status == "archived":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This goal is archived; unarchive it first")
    saved = _saved(db, goal)
    if saved + data.amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can't withdraw more than the ৳{saved:,.2f} saved toward this goal",
        )
    db.add(
        GoalContribution(
            goal_id=goal.id,
            user_id=current_user.id,
            amount=data.amount,
            contributed_on=data.contributed_on or app_today(),
            note=data.note,
        )
    )
    db.commit()
    return to_response(goal, saved + data.amount)


@router.delete("/{goal_id}/contributions/{contribution_id}", response_model=GoalResponse)
def delete_contribution(
    goal_id: UUID,
    contribution_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a contribution (e.g. entered by mistake). Returns the updated goal."""
    goal = _get_owned(db, goal_id, current_user)
    contribution = (
        db.query(GoalContribution)
        .filter(
            GoalContribution.id == contribution_id,
            GoalContribution.goal_id == goal_id,
            GoalContribution.user_id == current_user.id,
        )
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")
    remaining_saved = _saved(db, goal) - contribution.amount
    if remaining_saved < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Removing this would leave the goal below ৳0; remove the withdrawal first",
        )
    db.delete(contribution)
    db.commit()
    return to_response(goal, remaining_saved)
