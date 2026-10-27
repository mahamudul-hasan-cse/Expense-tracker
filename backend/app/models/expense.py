import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.category import Category


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
        # Indexes for common query patterns
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_category_id", "category_id"),
        Index("ix_expenses_date_category", "expense_date", "category_id"),
        Index("ix_expenses_created_at", "created_at"),
        # Per-user listing/stats: WHERE user_id = ? ORDER BY expense_date DESC, created_at DESC
        Index("ix_expenses_user_date", "user_id", "expense_date", "created_at"),
    )

    # Relationships
    category: Mapped[Category] = relationship("Category", back_populates="expenses")
