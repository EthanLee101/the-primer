"""replace mastery rolling_accuracy with bkt p_know

Revision ID: 6724cd975840
Revises: 80dc1c5f6a75
Create Date: 2026-09-23 20:51:35.685297

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6724cd975840"
down_revision: str | Sequence[str] | None = "80dc1c5f6a75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# app.mastery.P_INIT — duplicated as a literal rather than imported, since a
# migration's job is to describe a fixed point-in-time schema change, not to
# stay in sync with application code that may change P_INIT later.
_P_INIT = "0.05"


def upgrade() -> None:
    # server_default backfills existing rows (any mastery row from before
    # this migration) with the BKT prior, so this doesn't fail against a
    # populated table the way a bare `nullable=False` add would. Dropped
    # again afterward — going forward, the app (Mastery.p_know's own
    # default=P_INIT) is the one source of truth for new rows, not the DB.
    op.add_column(
        "mastery", sa.Column("p_know", sa.Float(), nullable=False, server_default=_P_INIT)
    )
    op.drop_column("mastery", "rolling_accuracy")
    op.alter_column("mastery", "p_know", server_default=None)


def downgrade() -> None:
    op.add_column("mastery", sa.Column("rolling_accuracy", sa.Float(), nullable=True))
    op.drop_column("mastery", "p_know")
