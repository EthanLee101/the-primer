"""add streak tracking to child

Revision ID: 6e92381e4d3f
Revises: d3a1a7f42243
Create Date: 2026-09-23 23:12:56.530843

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6e92381e4d3f"
down_revision: str | Sequence[str] | None = "d3a1a7f42243"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default backfills existing rows with 0 — same reasoning as the
    # p_know migration: dropped again afterward, since app.models.Child's
    # own default=0 is the source of truth for new rows going forward.
    op.add_column(
        "child", sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0")
    )
    # last_practice_date needs no server_default — NULL is a correct
    # backfill for every existing child, none of which has triggered the
    # new streak logic yet.
    op.add_column("child", sa.Column("last_practice_date", sa.Date(), nullable=True))
    op.alter_column("child", "current_streak", server_default=None)


def downgrade() -> None:
    op.drop_column("child", "last_practice_date")
    op.drop_column("child", "current_streak")
