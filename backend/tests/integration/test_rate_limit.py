from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Attempt, Child, Mastery

client = TestClient(app)


@pytest.fixture
def child_id() -> Iterator[int]:
    with SessionLocal() as db:
        child = Child(name="rate-limit-child")
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


def test_answer_endpoint_enforces_rate_limit(child_id: int) -> None:
    limit = int(get_settings().answer_rate_limit.split("/")[0])

    # one more attempt than the limit allows, each answered once
    attempt_ids = []
    for _ in range(limit + 1):
        response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
        attempt_ids.append(response.json()["attempt_id"])

    statuses = [
        client.post(f"/attempts/{aid}/answer", json={"submitted_answer": 0}).status_code
        for aid in attempt_ids
    ]

    assert statuses.count(200) == limit
    assert statuses[-1] == 429


def test_rate_limit_response_does_not_leak_internals(child_id: int) -> None:
    limit = int(get_settings().answer_rate_limit.split("/")[0])

    attempt_ids = []
    for _ in range(limit + 1):
        response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
        attempt_ids.append(response.json()["attempt_id"])

    for aid in attempt_ids[:limit]:
        client.post(f"/attempts/{aid}/answer", json={"submitted_answer": 0})

    response = client.post(f"/attempts/{attempt_ids[-1]}/answer", json={"submitted_answer": 0})
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Please wait a moment and try again."}


def test_login_endpoint_enforces_rate_limit() -> None:
    limit = int(get_settings().auth_rate_limit.split("/")[0])

    statuses = [
        client.post(
            "/parents/login", json={"email": "nobody@example.com", "password": "wrong password"}
        ).status_code
        for _ in range(limit + 1)
    ]

    # every one of these logins was invalid (401) except the last, which
    # should be blocked by the rate limiter before credentials are even checked
    assert statuses.count(401) == limit
    assert statuses[-1] == 429
