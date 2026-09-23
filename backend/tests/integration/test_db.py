from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Attempt, Child, Skill


def test_attempt_roundtrip() -> None:
    with SessionLocal() as db:
        child = Child(name="test-child")
        skill = Skill(code="addition_1digit", description="Single-digit addition")
        db.add_all([child, skill])
        db.flush()

        attempt = Attempt(
            child_id=child.id,
            skill_id=skill.id,
            difficulty=1,
            operand_a=3,
            operand_b=4,
            correct=True,
        )
        db.add(attempt)
        db.commit()

        stored = db.get(Attempt, attempt.id)
        assert stored is not None
        assert stored.correct is True
        assert stored.child.name == "test-child"
        assert stored.skill.code == "addition_1digit"

        db.execute(delete(Attempt).where(Attempt.id == attempt.id))
        db.execute(delete(Child).where(Child.id == child.id))
        db.execute(delete(Skill).where(Skill.id == skill.id))
        db.commit()
