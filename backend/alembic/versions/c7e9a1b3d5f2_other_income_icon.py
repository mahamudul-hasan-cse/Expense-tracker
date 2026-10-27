"""other_income_icon

The default income category "Other" used ➕, which looked like an "add" button
in the dashboard's Upcoming list. Use 💰 instead, for existing users too.
Only rows still exactly as created (default, named Other, icon ➕) are changed;
a user's own icon is left alone. Data-only, reversible.

Revision ID: c7e9a1b3d5f2
Revises: a3c5e7f9b1d2
Create Date: 2026-10-28

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c7e9a1b3d5f2"
down_revision: Union[str, None] = "a3c5e7f9b1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE income_categories SET icon = '💰' WHERE is_default AND name = 'Other' AND icon = '➕'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE income_categories SET icon = '➕' WHERE is_default AND name = 'Other' AND icon = '💰'"
    )
