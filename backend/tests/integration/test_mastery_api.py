from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.mastery import MIN_ATTEMPTS_BEFORE_ADJUST
from app.models import Attempt, Child, Mastery

client = TestClient(app)


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
    problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "addition"}
    ).json()
    correct = problem["operand_a"] + problem["operand_b"]
    client.post(f"/attempts/{problem['attempt_id']}/answer", json={"submitted_answer": correct})


def _answer_wrong(child_id: int) -> None:
    problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "addition"}
    ).json()
    wrong = problem["operand_a"] + problem["operand_b"] + 1000
    client.post(f"/attempts/{problem['attempt_id']}/answer", json={"submitted_answer": wrong})


def test_first_problem_starts_at_difficulty_one(child_id: int) -> None:
    problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "addition"}
    ).json()
    assert problem["difficulty"] == 1


def test_difficulty_rises_after_sustained_correct_answers(child_id: int) -> None:
    for _ in range(MIN_ATTEMPTS_BEFORE_ADJUST + 2):
        _answer_correctly(child_id)

    problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "addition"}
    ).json()
    assert problem["difficulty"] > 1


def test_difficulty_is_scoped_per_skill(child_id: int) -> None:
    for _ in range(MIN_ATTEMPTS_BEFORE_ADJUST + 2):
        _answer_correctly(child_id)

    subtraction_problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "subtraction"}
    ).json()
    assert subtraction_problem["difficulty"] == 1


def test_difficulty_falls_after_sustained_wrong_answers(child_id: int) -> None:
    for _ in range(MIN_ATTEMPTS_BEFORE_ADJUST + 2):
        _answer_correctly(child_id)
    for _ in range(MIN_ATTEMPTS_BEFORE_ADJUST + 2):
        _answer_wrong(child_id)

    problem = client.post(
        f"/children/{child_id}/problems", params={"skill": "addition"}
    ).json()
    assert problem["difficulty"] == 1
