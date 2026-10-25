from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.user import User
from app.security import hash_password

DEFAULT_CATEGORIES = [
    ("Rickshaw", "🛺"),
    ("Wifi Bill", "📶"),
    ("Random", "🎲"),
    ("Smoking", "🚬"),
]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def create_user(db: Session, email: str, password: str) -> User:
    """Create a user with the default categories. Caller commits."""
    user = User(email=email.strip().lower(), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    for name, icon in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user.id, name=name, icon=icon, is_default=True))
    return user
