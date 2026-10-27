from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.income import IncomeCategory
from app.models.user import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the user from the Bearer access token, or raise 401."""
    if credentials is None:
        raise _unauthorized("Not authenticated")

    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise _unauthorized("Invalid or expired token")

    try:
        user = db.get(User, UUID(payload["sub"]))
    except ValueError:
        user = None
    if user is None or user.token_version != payload["ver"]:
        raise _unauthorized("Invalid or expired token")
    return user


def get_user_category(db: Session, category_id: UUID, user: User) -> Category:
    """Return the user's category, or raise 400 (used when validating request bodies)."""
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == user.id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
    return category


def get_user_income_category(db: Session, income_category_id: UUID, user: User) -> IncomeCategory:
    """Return the user's income category, or raise 400 (used when validating request bodies)."""
    category = (
        db.query(IncomeCategory)
        .filter(IncomeCategory.id == income_category_id, IncomeCategory.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Income category not found")
    return category
