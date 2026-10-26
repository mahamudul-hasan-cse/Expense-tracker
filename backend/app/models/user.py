import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # stored lowercased
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Incremented on logout to revoke all previously issued tokens
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # The AI assistant is opt-in: off until the user turns it on
    assistant_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
