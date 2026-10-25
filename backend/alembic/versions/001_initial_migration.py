"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    
    # Create expenses table
    op.create_table(
        'expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint('amount > 0', name='check_amount_positive')
    )
    
    # Create recurring_expenses table
    op.create_table(
        'recurring_expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False),
        sa.Column('due_day', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_reminded_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.CheckConstraint('amount > 0', name='check_recurring_amount_positive'),
        sa.CheckConstraint("frequency IN ('weekly', 'monthly')", name='check_frequency_valid'),
        sa.CheckConstraint('due_day >= 1 AND due_day <= 31', name='check_due_day_range')
    )
    
    # Create indexes
    op.create_index('idx_expenses_date', 'expenses', ['expense_date'], postgresql_ops={'expense_date': 'DESC'})
    op.create_index('idx_expenses_category', 'expenses', ['category_id'])
    op.create_index('idx_expenses_date_category', 'expenses', ['expense_date', 'category_id'])
    
    # Seed default categories
    op.execute("""
        INSERT INTO categories (name, icon, is_default) VALUES
        ('Rickshaw', '🛺', true),
        ('Wifi Bill', '📶', true),
        ('Random', '🎲', true),
        ('Smoking', '🚬', true)
    """)


def downgrade() -> None:
    op.drop_index('idx_expenses_date_category')
    op.drop_index('idx_expenses_category')
    op.drop_index('idx_expenses_date')
    op.drop_table('recurring_expenses')
    op.drop_table('expenses')
    op.drop_table('categories')
