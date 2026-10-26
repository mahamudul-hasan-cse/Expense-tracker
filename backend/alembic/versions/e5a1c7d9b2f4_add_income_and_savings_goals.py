"""add_income_and_savings_goals

Adds income tracking (income_categories, incomes), savings goals
(savings_goals, goal_contributions) and extends recurring_expenses so one
mechanism covers recurring bills and recurring income:
  - kind ('expense' | 'income'), default 'expense' (existing rows keep working)
  - income_category_id, and category_id becomes nullable (exactly one is set)
  - last_paid_on (the due date of the last cycle marked paid/received)

Default income categories are seeded for every existing user. No existing data
is changed or removed.

Downgrade note: deletes recurring *income* items (they can't exist in the old
schema) and all income/goal data.

Revision ID: e5a1c7d9b2f4
Revises: c3a9d5e7f8b1
Create Date: 2026-10-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5a1c7d9b2f4"
down_revision: Union[str, None] = "c3a9d5e7f8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "income_categories",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "uq_income_categories_user_name", "income_categories", ["user_id", sa.text("lower(name)")], unique=True
    )

    op.create_table(
        "incomes",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("income_category_id", UUID, sa.ForeignKey("income_categories.id"), nullable=False),
        sa.Column("income_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("amount > 0", name="check_income_amount_positive"),
    )
    op.create_index("ix_incomes_user_date", "incomes", ["user_id", "income_date", "created_at"])
    op.create_index("ix_incomes_income_category_id", "incomes", ["income_category_id"])

    op.create_table(
        "savings_goals",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("target_amount > 0", name="check_goal_target_positive"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="check_goal_status_valid"),
    )
    op.create_index("uq_savings_goals_user_name", "savings_goals", ["user_id", sa.text("lower(name)")], unique=True)

    op.create_table(
        "goal_contributions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("goal_id", UUID, sa.ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("contributed_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("amount <> 0", name="check_contribution_nonzero"),
    )
    op.create_index("ix_goal_contributions_goal", "goal_contributions", ["goal_id", "contributed_on"])
    op.create_index("ix_goal_contributions_user_date", "goal_contributions", ["user_id", "contributed_on"])

    # Recurring items: one mechanism for bills and income
    op.add_column(
        "recurring_expenses", sa.Column("kind", sa.String(10), nullable=False, server_default="expense")
    )
    op.add_column(
        "recurring_expenses",
        sa.Column("income_category_id", UUID, sa.ForeignKey("income_categories.id"), nullable=True),
    )
    op.add_column("recurring_expenses", sa.Column("last_paid_on", sa.Date(), nullable=True))
    op.alter_column("recurring_expenses", "category_id", nullable=True)
    op.create_check_constraint("check_recurring_kind_valid", "recurring_expenses", "kind IN ('expense', 'income')")
    op.create_check_constraint(
        "check_recurring_kind_category",
        "recurring_expenses",
        "(kind = 'expense' AND category_id IS NOT NULL AND income_category_id IS NULL) OR "
        "(kind = 'income' AND income_category_id IS NOT NULL AND category_id IS NULL)",
    )

    # Default income categories for existing users (new users get them at registration)
    op.execute(
        """
        INSERT INTO income_categories (user_id, name, icon, is_default)
        SELECT u.id, d.name, d.icon, true
        FROM users u
        CROSS JOIN (VALUES
            ('Salary', '💼'), ('Freelance', '💻'), ('Business', '🏪'), ('Gift', '🎁'), ('Other', '➕')
        ) AS d(name, icon)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM recurring_expenses WHERE kind = 'income'")
    op.drop_constraint("check_recurring_kind_category", "recurring_expenses", type_="check")
    op.drop_constraint("check_recurring_kind_valid", "recurring_expenses", type_="check")
    op.alter_column("recurring_expenses", "category_id", nullable=False)
    op.drop_column("recurring_expenses", "last_paid_on")
    op.drop_column("recurring_expenses", "income_category_id")
    op.drop_column("recurring_expenses", "kind")

    op.drop_index("ix_goal_contributions_user_date", table_name="goal_contributions")
    op.drop_index("ix_goal_contributions_goal", table_name="goal_contributions")
    op.drop_table("goal_contributions")
    op.drop_index("uq_savings_goals_user_name", table_name="savings_goals")
    op.drop_table("savings_goals")
    op.drop_index("ix_incomes_income_category_id", table_name="incomes")
    op.drop_index("ix_incomes_user_date", table_name="incomes")
    op.drop_table("incomes")
    op.drop_index("uq_income_categories_user_name", table_name="income_categories")
    op.drop_table("income_categories")
