"""seed skill reference data

Revision ID: 0d506310ae7e
Revises: bd82286e7c1c
Create Date: 2026-09-22 20:44:30.836681

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0d506310ae7e'
down_revision: str | Sequence[str] | None = 'bd82286e7c1c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

skill_table = sa.table(
    "skill",
    sa.column("code", sa.String),
    sa.column("description", sa.String),
)

SKILLS = [
    {"code": "addition", "description": "Addition of two whole numbers"},
    {"code": "subtraction", "description": "Subtraction of two whole numbers"},
    {"code": "multiplication", "description": "Multiplication of two whole numbers"},
    {"code": "division", "description": "Division of two whole numbers with an integer result"},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(skill_table, SKILLS)


def downgrade() -> None:
    """Downgrade schema."""
    codes = [s["code"] for s in SKILLS]
    op.execute(skill_table.delete().where(skill_table.c.code.in_(codes)))
