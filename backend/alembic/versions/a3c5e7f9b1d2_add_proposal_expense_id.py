"""add_proposal_expense_id

Quick-add confirm is done by the server: remember which expense a confirmed
proposal created, so a retried confirm returns it instead of adding a duplicate.
Additive only.

Revision ID: a3c5e7f9b1d2
Revises: f7b3d2a8c6e1
Create Date: 2026-10-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3c5e7f9b1d2"
down_revision: Union[str, None] = "f7b3d2a8c6e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistant_messages",
        sa.Column(
            "proposal_expense_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expenses.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_messages", "proposal_expense_id")
