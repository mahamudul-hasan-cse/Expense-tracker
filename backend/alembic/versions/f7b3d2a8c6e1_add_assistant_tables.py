"""add_assistant_tables

AI assistant: conversations, messages, per-request usage (no message content),
cached insights, and users.assistant_enabled (opt-in, default false).
Additive only.

Revision ID: f7b3d2a8c6e1
Revises: e5a1c7d9b2f4
Create Date: 2026-10-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7b3d2a8c6e1"
down_revision: Union[str, None] = "e5a1c7d9b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def user_fk() -> sa.ForeignKey:
    # A ForeignKey object can only belong to one column, so make a new one each time
    return sa.ForeignKey("users.id", ondelete="CASCADE")


NOW = sa.text("NOW()")
NEW_ID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.add_column("users", sa.Column("assistant_enabled", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "assistant_conversations",
        sa.Column("id", UUID, primary_key=True, server_default=NEW_ID),
        sa.Column("user_id", UUID, user_fk(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_assistant_conversations_user_updated", "assistant_conversations", ["user_id", "updated_at"])

    op.create_table(
        "assistant_messages",
        sa.Column("id", UUID, primary_key=True, server_default=NEW_ID),
        sa.Column(
            "conversation_id", UUID, sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", UUID, user_fk(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("proposal", postgresql.JSONB(), nullable=True),
        sa.Column("proposal_status", sa.String(10), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="check_assistant_message_role"),
    )
    op.create_index("ix_assistant_messages_conversation", "assistant_messages", ["conversation_id", "created_at"])
    op.create_index("ix_assistant_messages_user_created", "assistant_messages", ["user_id", "role", "created_at"])

    op.create_table(
        "assistant_usage",
        sa.Column("id", UUID, primary_key=True, server_default=NEW_ID),
        sa.Column("user_id", UUID, user_fk(), nullable=False),
        sa.Column("conversation_id", UUID, nullable=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_assistant_usage_user_created", "assistant_usage", ["user_id", "created_at"])
    op.create_index("ix_assistant_usage_created", "assistant_usage", ["created_at"])

    op.create_table(
        "assistant_insights",
        sa.Column("id", UUID, primary_key=True, server_default=NEW_ID),
        sa.Column("user_id", UUID, user_fk(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("generated_for", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("user_id", "kind", "generated_for", name="uq_assistant_insight_per_day"),
    )


def downgrade() -> None:
    op.drop_table("assistant_insights")
    op.drop_index("ix_assistant_usage_created", table_name="assistant_usage")
    op.drop_index("ix_assistant_usage_user_created", table_name="assistant_usage")
    op.drop_table("assistant_usage")
    op.drop_index("ix_assistant_messages_user_created", table_name="assistant_messages")
    op.drop_index("ix_assistant_messages_conversation", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_index("ix_assistant_conversations_user_updated", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
    op.drop_column("users", "assistant_enabled")
