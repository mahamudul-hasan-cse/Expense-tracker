import uuid
from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey, func, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)  # Monthly budget limit
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("amount >= 0", name="check_budget_amount_non_negative"),
        CheckConstraint("month >= 1 AND month <= 12", name="check_month_valid"),
        UniqueConstraint("category_id", "month", "year", name="unique_category_month_year"),
        Index("ix_budgets_user_period", "user_id", "year", "month"),
    )

    # Relationships
    category = relationship("Category")
