import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# A quick-add card can be confirmed for this long; after that it shows as expired
PROPOSAL_TTL = timedelta(hours=24)


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_assistant_conversations_user_updated", "user_id", "updated_at"),)

    messages: Mapped[list["AssistantMessage"]] = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssistantMessage.created_at",
    )


class AssistantMessage(Base):
    """A user or assistant turn. Tool traffic is not stored, only final text and proposals."""

    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Quick-add: a proposed expense the user can confirm (never saved by the model)
    proposal: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    proposal_status: Mapped[str | None] = mapped_column(String(10), nullable=True)  # pending|confirmed|cancelled
    # The expense created on confirm; a retried confirm returns this instead of adding another
    proposal_expense_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="ok")  # ok|interrupted|error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_assistant_message_role"),
        Index("ix_assistant_messages_conversation", "conversation_id", "created_at"),
        Index("ix_assistant_messages_user_created", "user_id", "role", "created_at"),
    )

    conversation: Mapped[AssistantConversation] = relationship("AssistantConversation", back_populates="messages")

    @property
    def proposal_state(self) -> str | None:
        """proposal_status, plus "expired" for a pending proposal older than PROPOSAL_TTL."""
        if self.proposal_status == "pending" and self.proposal_expired:
            return "expired"
        return self.proposal_status

    @property
    def proposal_expired(self) -> bool:
        return self.created_at is not None and datetime.now(timezone.utc) - self.created_at > PROPOSAL_TTL


class AssistantUsage(Base):
    """One row per LLM request, for limits and cost reporting. Never stores message content."""

    __tablename__ = "assistant_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Not a foreign key: usage outlives deleted conversations (cost accounting)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # chat | insight
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # ok | error code
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_assistant_usage_user_created", "user_id", "created_at"),
        Index("ix_assistant_usage_created", "created_at"),
    )


class AssistantInsight(Base):
    """Cached AI-written summaries (weekly insight), at most one per user per kind per day."""

    __tablename__ = "assistant_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_for: Mapped[date] = mapped_column(Date, nullable=False)  # Asia/Dhaka date
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "kind", "generated_for", name="uq_assistant_insight_per_day"),)
