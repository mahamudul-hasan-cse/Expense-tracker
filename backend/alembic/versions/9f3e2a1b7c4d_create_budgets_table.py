"""create_budgets_table

The earlier add_budgets_table revision was generated empty (the Budget model
was not imported in env.py), so the table was never created. This revision
creates it, skipping creation if it already exists.

Revision ID: 9f3e2a1b7c4d
Revises: 4b49f5a9eb63
Create Date: 2026-10-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9f3e2a1b7c4d'
down_revision: Union[str, None] = '4b49f5a9eb63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table('budgets'):
        return

    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint('amount >= 0', name='check_budget_amount_non_negative'),
        sa.CheckConstraint('month >= 1 AND month <= 12', name='check_month_valid'),
        sa.UniqueConstraint('category_id', 'month', 'year', name='unique_category_month_year'),
    )


def downgrade() -> None:
    op.drop_table('budgets')
