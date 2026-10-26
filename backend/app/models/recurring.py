import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.category import Category


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # weekly | monthly
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-7 for weekly, 1-31 for monthly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    last_reminded_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_recurring_amount_positive"),
        CheckConstraint("frequency IN ('weekly', 'monthly')", name="check_frequency_valid"),
        CheckConstraint("due_day >= 1 AND due_day <= 31", name="check_due_day_range"),
        # Index for filtering active recurring expenses
        Index("ix_recurring_is_active", "is_active"),
        Index("ix_recurring_user_active", "user_id", "is_active"),
    )

    # Relationships
    category: Mapped[Category] = relationship("Category", back_populates="recurring_expenses")
