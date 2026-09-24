"""DB glue for Mastery rows — translates between app/mastery.py's pure
MasteryState and the persisted Mastery ORM row. Kept separate from
app/mastery.py so the adjustment math stays DB-free and independently
testable; this module is the only place that touches the database for it.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.mastery import MasteryState
from app.models import Mastery


def get_or_create_mastery(db: Session, child_id: int, skill_id: int) -> Mastery:
    # a plain "SELECT, then INSERT if missing" has a race: two concurrent
    # requests for the same (child, skill) can both miss the SELECT and both
    # try to INSERT, so the second hits the unique constraint. INSERT ...
    # ON CONFLICT DO NOTHING is atomic at the DB level, so there's no window
    # where two requests can both believe they're the one creating the row.
    stmt = pg_insert(Mastery).values(child_id=child_id, skill_id=skill_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=["child_id", "skill_id"])
    db.execute(stmt)
    db.flush()

    row = db.scalar(
        select(Mastery).where(Mastery.child_id == child_id, Mastery.skill_id == skill_id)
    )
    assert row is not None  # guaranteed by the insert (ours or a concurrent one) above
    return row


def to_state(row: Mastery) -> MasteryState:
    return MasteryState(
        difficulty=row.difficulty,
        p_know=row.p_know,
        attempts_count=row.attempts_count,
        correct_count=row.correct_count,
    )


def apply_state(row: Mastery, state: MasteryState) -> None:
    row.difficulty = state.difficulty
    row.p_know = state.p_know
    row.attempts_count = state.attempts_count
    row.correct_count = state.correct_count
