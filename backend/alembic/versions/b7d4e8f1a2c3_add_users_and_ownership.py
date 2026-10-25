"""add_users_and_ownership

Adds the users table and a user_id owner column to categories, expenses,
recurring_expenses and budgets.

Existing rows: if any of those tables has rows, an owner account is created and
every existing row is assigned to it. Nothing is deleted.
  - Email: OWNER_EMAIL env var (default "owner@localhost")
  - Password: OWNER_PASSWORD env var. If unset, the account gets an unusable
    password; set one later with:  uv run python -m app.cli set-password <email>

Category names become unique per user (case-insensitive) instead of globally.

Revision ID: b7d4e8f1a2c3
Revises: 9f3e2a1b7c4d
Create Date: 2026-10-25

"""
import os
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7d4e8f1a2c3'
down_revision: Union[str, None] = '9f3e2a1b7c4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OWNED_TABLES = ("categories", "expenses", "recurring_expenses", "budgets")


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    bind = op.get_bind()
    has_rows = any(
        bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar()
        for table in OWNED_TABLES
    )

    owner_id = None
    if has_rows:
        email = os.environ.get("OWNER_EMAIL", "owner@localhost").strip().lower()
        password = os.environ.get("OWNER_PASSWORD")
        if password:
            from argon2 import PasswordHasher
            password_hash = PasswordHasher().hash(password)
        else:
            password_hash = "!"  # not a valid argon2 hash, so login is impossible until reset
        owner_id = str(uuid.uuid4())
        bind.execute(
            sa.text("INSERT INTO users (id, email, password_hash) VALUES (CAST(:id AS uuid), :email, :hash)"),
            {"id": owner_id, "email": email, "hash": password_hash},
        )

    for table in OWNED_TABLES:
        op.add_column(table, sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
        if owner_id:
            bind.execute(sa.text(f"UPDATE {table} SET user_id = CAST(:id AS uuid)"), {"id": owner_id})
        op.alter_column(table, 'user_id', nullable=False)
        op.create_foreign_key(f'fk_{table}_user_id', table, 'users', ['user_id'], ['id'], ondelete='CASCADE')
        op.create_index(f'ix_{table}_user_id', table, ['user_id'])

    # Category names: globally unique -> unique per user, case-insensitive
    op.drop_constraint('categories_name_key', 'categories', type_='unique')
    op.create_index('uq_categories_user_name', 'categories', ['user_id', sa.text('lower(name)')], unique=True)


def downgrade() -> None:
    # Note: fails if two users have categories with the same name
    op.drop_index('uq_categories_user_name', table_name='categories')
    op.create_unique_constraint('categories_name_key', 'categories', ['name'])

    for table in OWNED_TABLES:
        op.drop_index(f'ix_{table}_user_id', table_name=table)
        op.drop_constraint(f'fk_{table}_user_id', table, type_='foreignkey')
        op.drop_column(table, 'user_id')

    op.drop_table('users')
