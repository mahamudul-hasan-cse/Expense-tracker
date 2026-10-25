import uuid
from sqlalchemy import Column, String, Numeric, Integer, Boolean, Date, DateTime, ForeignKey, func, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    frequency = Column(String(20), nullable=False)  # 'weekly' or 'monthly'
    due_day = Column(Integer, nullable=False)  # 1-7 for weekly, 1-31 for monthly
    is_active = Column(Boolean, default=True)
    last_reminded_at = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_recurring_amount_positive"),
        CheckConstraint("frequency IN ('weekly', 'monthly')", name="check_frequency_valid"),
        CheckConstraint("due_day >= 1 AND due_day <= 31", name="check_due_day_range"),
        # Index for filtering active recurring expenses
        Index("ix_recurring_is_active", "is_active"),
    )

    # Relationships
    category = relationship("Category", back_populates="recurring_expenses")
