import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Attempt, Child, Mastery

client = TestClient(app)


@pytest.fixture
def child_id() -> Iterator[uuid.UUID]:
    with SessionLocal() as db:
        child = Child(name="test-child")
        db.add(child)
        db.commit()
        db.refresh(child)
        cid = child.public_id
        internal_id = child.id

    yield cid

    with SessionLocal() as db:
        db.query(Attempt).filter(Attempt.child_id == internal_id).delete()
        db.query(Mastery).filter(Mastery.child_id == internal_id).delete()
        db.query(Child).filter(Child.id == internal_id).delete()
        db.commit()


def test_full_problem_and_answer_flow(child_id: uuid.UUID) -> None:
    response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
    assert response.status_code == 201
    problem = response.json()
    assert problem["skill_code"] == "addition"
    correct_answer = problem["operand_a"] + problem["operand_b"]

    response = client.post(
        f"/attempts/{problem['attempt_id']}/answer",
        json={"submitted_answer": correct_answer},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["correct_answer"] == correct_answer
    assert body["explanation"] is None  # no LLM call on a correct answer


def test_wrong_answer_is_graded_correctly(child_id: uuid.UUID) -> None:
    response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
    problem = response.json()
    correct_answer = problem["operand_a"] + problem["operand_b"]

    response = client.post(
        f"/attempts/{problem['attempt_id']}/answer",
        json={"submitted_answer": correct_answer + 1},
    )
    body = response.json()
    assert body["correct"] is False
    assert body["correct_answer"] == correct_answer
    assert body["explanation"] is not None  # fake provider still returns something in tests


def test_cannot_answer_same_attempt_twice(child_id: uuid.UUID) -> None:
    response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
    attempt_id = response.json()["attempt_id"]

    first = client.post(f"/attempts/{attempt_id}/answer", json={"submitted_answer": 0})
    assert first.status_code == 200

    second = client.post(f"/attempts/{attempt_id}/answer", json={"submitted_answer": 0})
    assert second.status_code == 409


def test_answering_unknown_attempt_404s() -> None:
    response = client.post(f"/attempts/{uuid.uuid4()}/answer", json={"submitted_answer": 0})
    assert response.status_code == 404


def test_unknown_skill_400s(child_id: uuid.UUID) -> None:
    response = client.post(f"/children/{child_id}/problems", params={"skill": "calculus"})
    assert response.status_code == 400


def test_unknown_child_404s() -> None:
    response = client.post(f"/children/{uuid.uuid4()}/problems", params={"skill": "addition"})
    assert response.status_code == 404
