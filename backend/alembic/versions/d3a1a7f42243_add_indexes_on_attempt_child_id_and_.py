"""add indexes on attempt.child_id and child.parent_id

Revision ID: d3a1a7f42243
Revises: 67d371402abe
Create Date: 2026-09-23 23:09:59.171119

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3a1a7f42243"
down_revision: str | Sequence[str] | None = "67d371402abe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_attempt_child_id", "attempt", ["child_id"])
    op.create_index("ix_child_parent_id", "child", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_child_parent_id", table_name="child")
    op.drop_index("ix_attempt_child_id", table_name="attempt")
