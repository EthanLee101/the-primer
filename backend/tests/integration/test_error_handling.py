from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Attempt, Child, Mastery

client = TestClient(app)


@pytest.fixture
def child_id() -> Iterator[int]:
    with SessionLocal() as db:
        child = Child(name="error-handling-child")
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


def test_unhandled_exception_returns_generic_body_not_a_traceback(child_id: int) -> None:
    response = client.post(f"/children/{child_id}/problems", params={"skill": "addition"})
    attempt_id = response.json()["attempt_id"]

    # Starlette's ServerErrorMiddleware sends the handled response to the
    # client, then re-raises the original exception so the default
    # TestClient can surface it for debugging — a real deployed server never
    # does this; the client only ever sees the response. raise_server_exceptions=False
    # here reproduces what an actual HTTP client would receive.
    no_raise_client = TestClient(app, raise_server_exceptions=False)

    secret_looking_message = "psycopg2.OperationalError: password authentication failed for user X"
    with patch(
        "app.routers.attempts.get_or_create_mastery",
        side_effect=RuntimeError(secret_looking_message),
    ):
        response = no_raise_client.post(
            f"/attempts/{attempt_id}/answer", json={"submitted_answer": 0}
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong. Please try again."}
    assert secret_looking_message not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


def test_known_http_exceptions_are_unaffected_by_the_generic_handler() -> None:
    # a deliberate, controlled 404 should still say exactly what it says —
    # the generic handler must only catch genuinely unexpected exceptions
    response = client.post("/attempts/999999999/answer", json={"submitted_answer": 0})
    assert response.status_code == 404
    assert response.json() == {"detail": "attempt not found"}
