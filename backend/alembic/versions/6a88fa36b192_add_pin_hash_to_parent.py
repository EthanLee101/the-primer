"""add pin hash to parent

Revision ID: 6a88fa36b192
Revises: 6e92381e4d3f
Create Date: 2026-09-24 14:31:57.335309

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a88fa36b192"
down_revision: str | Sequence[str] | None = "6e92381e4d3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # nullable, no server_default needed — NULL is a correct backfill for
    # every existing parent, none of whom has set a PIN yet (opt-in, via
    # POST /parents/me/pin).
    op.add_column("parent", sa.Column("pin_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("parent", "pin_hash")
