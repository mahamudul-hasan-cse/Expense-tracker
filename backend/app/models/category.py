import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Category names are unique per user, case-insensitively
    __table_args__ = (
        Index("uq_categories_user_name", "user_id", text("lower(name)"), unique=True),
    )

    # Relationships
    expenses = relationship("Expense", back_populates="category")
    recurring_expenses = relationship("RecurringExpense", back_populates="category")
