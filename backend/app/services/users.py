from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.income import IncomeCategory
from app.models.user import User
from app.security import hash_password

DEFAULT_CATEGORIES = [
    ("Rickshaw", "🛺"),
    ("Wifi Bill", "📶"),
    ("Random", "🎲"),
    ("Smoking", "🚬"),
]

# Keep in sync with the seed in the add_income_and_savings_goals migration
DEFAULT_INCOME_CATEGORIES = [
    ("Salary", "💼"),
    ("Freelance", "💻"),
    ("Business", "🏪"),
    ("Gift", "🎁"),
    ("Other", "➕"),
]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def create_user(db: Session, email: str, password: str) -> User:
    """Create a user with the default expense and income categories. Caller commits."""
    user = User(email=email.strip().lower(), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    for name, icon in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user.id, name=name, icon=icon, is_default=True))
    for name, icon in DEFAULT_INCOME_CATEGORIES:
        db.add(IncomeCategory(user_id=user.id, name=name, icon=icon, is_default=True))
    return user
