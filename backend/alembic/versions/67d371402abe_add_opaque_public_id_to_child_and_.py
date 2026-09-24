"""add opaque public_id to child and attempt

Revision ID: 67d371402abe
Revises: 6724cd975840
Create Date: 2026-09-23 21:40:53.519874

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "67d371402abe"
down_revision: str | Sequence[str] | None = "6724cd975840"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgcrypto's gen_random_uuid() backfills a distinct UUID per existing
    # row as the column is added — a single literal server_default (as
    # used for the p_know migration) can't work here since every row needs
    # a *different* value, not a shared one. Dropped again after backfill,
    # same reasoning as that migration: going forward, the app
    # (Child/Attempt.public_id's own default=uuid.uuid4) is the one source
    # of truth for new rows, not the DB.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.add_column(
        "child",
        sa.Column(
            "public_id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
    )
    op.create_unique_constraint("uq_child_public_id", "child", ["public_id"])
    op.alter_column("child", "public_id", server_default=None)

    op.add_column(
        "attempt",
        sa.Column(
            "public_id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
    )
    op.create_unique_constraint("uq_attempt_public_id", "attempt", ["public_id"])
    op.alter_column("attempt", "public_id", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_attempt_public_id", "attempt", type_="unique")
    op.drop_column("attempt", "public_id")

    op.drop_constraint("uq_child_public_id", "child", type_="unique")
    op.drop_column("child", "public_id")

    # pgcrypto is left in place deliberately — other objects in the
    # database may already depend on it, and dropping/recreating a
    # database-wide extension as part of one table's downgrade isn't safe
    # to assume is reversible.
