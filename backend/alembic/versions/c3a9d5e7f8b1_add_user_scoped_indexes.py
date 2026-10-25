"""add_user_scoped_indexes

Every query is now filtered by user_id, so the hot paths get composite indexes
that lead with user_id. The single-column user_id indexes they make redundant
are dropped (indexes only; no data changes).

Revision ID: c3a9d5e7f8b1
Revises: b7d4e8f1a2c3
Create Date: 2026-10-26

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3a9d5e7f8b1'
down_revision: Union[str, None] = 'b7d4e8f1a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_expenses_user_date', 'expenses', ['user_id', 'expense_date', 'created_at'])
    op.create_index('ix_recurring_user_active', 'recurring_expenses', ['user_id', 'is_active'])
    op.create_index('ix_budgets_user_period', 'budgets', ['user_id', 'year', 'month'])

    op.drop_index('ix_expenses_user_id', table_name='expenses')
    op.drop_index('ix_recurring_expenses_user_id', table_name='recurring_expenses')
    op.drop_index('ix_budgets_user_id', table_name='budgets')
    # uq_categories_user_name (user_id, lower(name)) covers user_id lookups
    op.drop_index('ix_categories_user_id', table_name='categories')


def downgrade() -> None:
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('ix_recurring_expenses_user_id', 'recurring_expenses', ['user_id'])
    op.create_index('ix_expenses_user_id', 'expenses', ['user_id'])

    op.drop_index('ix_budgets_user_period', table_name='budgets')
    op.drop_index('ix_recurring_user_active', table_name='recurring_expenses')
    op.drop_index('ix_expenses_user_date', table_name='expenses')
