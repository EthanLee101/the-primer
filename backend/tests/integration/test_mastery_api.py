from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Attempt, Child, Mastery

client = TestClient(app)

# BKT's Bayesian update naturally requires accumulated evidence before
# p_know moves far — no artificial "wait N attempts" gate needed the way
# the old rolling-accuracy engine's MIN_ATTEMPTS_BEFORE_ADJUST had. This
# many attempts is enough to see a clear rise (see tests/unit/test_mastery.py
# for the underlying curve).
STREAK_LENGTH = 6

# Difficulty is rate-limited to move at most one level per attempt (see
# MAX_DIFFICULTY_STEP in app/mastery.py) — climbing back down from a peak
# takes more attempts than the belief itself needs to collapse, so the
# recovery streak here is longer than the climb that produces the peak.
RECOVERY_LENGTH = 8


@pytest.fixture
def child_id() -> Iterator[int]:
    with SessionLocal() as db:
        child = Child(name="test-child")
        db.add(child)
        db.commit()
        db.refresh(child)
        cid = child.id

    yield cid

    with SessionLocal() as db:
        db.query(Attempt).filter(Attempt.child_id == cid).delete()
        db.query(Mastery).filter(Mastery.child_id == cid).delete()
        db.query(Child).filter(Child.id == cid).delete()
        db.commit()


def _answer_correctly(child_id: int) -> None:
    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    correct = problem["operand_a"] + problem["operand_b"]
    client.post(f"/attempts/{problem['attempt_id']}/answer", json={"submitted_answer": correct})


def _answer_wrong(child_id: int) -> None:
    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    wrong = problem["operand_a"] + problem["operand_b"] + 1000
    client.post(f"/attempts/{problem['attempt_id']}/answer", json={"submitted_answer": wrong})


def test_first_problem_starts_at_difficulty_one(child_id: int) -> None:
    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    assert problem["difficulty"] == 1


def test_difficulty_rises_after_sustained_correct_answers(child_id: int) -> None:
    for _ in range(STREAK_LENGTH):
        _answer_correctly(child_id)

    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    assert problem["difficulty"] > 1


def test_difficulty_is_scoped_per_skill(child_id: int) -> None:
    for _ in range(STREAK_LENGTH):
        _answer_correctly(child_id)

    subtraction_problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "subtraction"}
    ).json()
    assert subtraction_problem["difficulty"] == 1


def test_difficulty_falls_after_sustained_wrong_answers(child_id: int) -> None:
    for _ in range(STREAK_LENGTH):
        _answer_correctly(child_id)
    peak = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()[
        "difficulty"
    ]
    assert peak > 1

    for _ in range(RECOVERY_LENGTH):
        _answer_wrong(child_id)

    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    assert problem["difficulty"] < peak
    assert problem["difficulty"] == 1
