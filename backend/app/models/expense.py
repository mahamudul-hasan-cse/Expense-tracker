import uuid
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, func, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(12, 2), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    note = Column(String(500), nullable=True)
    expense_date = Column(Date, nullable=False, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
        # Indexes for common query patterns
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_category_id", "category_id"),
        Index("ix_expenses_date_category", "expense_date", "category_id"),
        Index("ix_expenses_created_at", "created_at"),
    )

    # Relationships
    category = relationship("Category", back_populates="expenses")
