import threading

from sqlalchemy import select

from app.db import SessionLocal
from app.mastery_repo import get_or_create_mastery
from app.models import Child, Mastery, Skill


def test_get_or_create_mastery_is_safe_under_real_concurrency() -> None:
    """Regression test for a real bug caught by manually running the app: the
    original implementation did a plain SELECT, then INSERT if nothing was
    found. Two requests for a brand-new (child, skill) pair that overlapped
    in time could both miss the SELECT and both attempt the INSERT, so the
    second raised a UniqueViolation — reproduced in practice by React
    StrictMode firing two near-simultaneous requests in dev.

    A plain thread-based test isn't reliable here: the original race window
    is only a handful of bytecode instructions plus one fast local round
    trip, so unsynchronized threads can pass even against the buggy code
    (verified by hand — a worse test than no test, since it'd pass or fail
    non-deterministically for reasons unrelated to a real regression).

    Instead, this forces genuine overlap deterministically: a second request
    is started while the first is deliberately left uncommitted, so Postgres
    itself blocks the second on the pending unique-index insert rather than
    us hoping for an unlucky interleaving. The fix (INSERT ... ON CONFLICT DO
    NOTHING) means the second request waits, then safely no-ops once the
    first commits, instead of raising.
    """
    with SessionLocal() as db:
        child = Child(name="race-child")
        db.add(child)
        db.commit()
        db.refresh(child)
        child_id = child.id
        skill = db.scalar(select(Skill).where(Skill.code == "addition"))
        assert skill is not None
        skill_id = skill.id

    session_a = SessionLocal()
    get_or_create_mastery(session_a, child_id, skill_id)  # flushed, deliberately not committed

    errors: list[BaseException] = []
    second_request_done = threading.Event()

    def second_request() -> None:
        try:
            with SessionLocal() as session_b:
                get_or_create_mastery(session_b, child_id, skill_id)
                session_b.commit()
        except BaseException as exc:  # noqa: BLE001 — capture anything, including DB errors
            errors.append(exc)
        finally:
            second_request_done.set()

    thread = threading.Thread(target=second_request)
    thread.start()
    # proves real overlap happened: session_b must still be blocked on
    # session_a's uncommitted insert, not racing past it by luck
    assert not second_request_done.wait(timeout=0.3)

    session_a.commit()
    session_a.close()
    thread.join(timeout=5)

    assert errors == []

    with SessionLocal() as db:
        rows = db.scalars(
            select(Mastery).where(Mastery.child_id == child_id, Mastery.skill_id == skill_id)
        ).all()
        assert len(rows) == 1

        db.query(Mastery).filter(Mastery.child_id == child_id).delete()
        db.query(Child).filter(Child.id == child_id).delete()
        db.commit()
