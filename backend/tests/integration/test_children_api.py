import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import Child

client = TestClient(app)


def test_create_child() -> None:
    response = client.post("/children", json={"name": "Ada"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada"
    assert "id" in body and "created_at" in body
    assert body["current_streak"] == 0
    # the exposed id must be an opaque, unguessable identifier, never the
    # sequential internal PK — see test_internal_id_cannot_be_used_to_reach_a_child
    assert uuid.UUID(body["id"])

    with SessionLocal() as db:
        db.query(Child).filter(Child.public_id == body["id"]).delete()
        db.commit()


def test_create_child_rejects_empty_name() -> None:
    response = client.post("/children", json={"name": ""})
    assert response.status_code == 422


def test_internal_id_cannot_be_used_to_reach_a_child() -> None:
    """Regression test for the enumeration gap this closed: child_id used
    to be the sequential internal PK, so anyone scanning small integers in
    a URL could find real children and read their name/practice history —
    a real risk once this app is on a public, crawlable URL, not just
    localhost. Proves the fix by using a real child's own actual internal
    PK (not a made-up number) as the path param and confirming it's
    rejected outright, not just "not found" — it's not even a valid id
    shape anymore, since the route only accepts a UUID."""
    response = client.post("/children", json={"name": "enumeration-test-kid"})
    public_id = response.json()["id"]

    with SessionLocal() as db:
        child = db.scalar(select(Child).where(Child.public_id == public_id))
        assert child is not None
        internal_id = child.id

        attempt = client.post(f"/children/{internal_id}/problems", params={"skill": "addition"})
        assert attempt.status_code == 422  # not even a valid path param, let alone found

        db.delete(child)
        db.commit()


def test_get_child_returns_current_state() -> None:
    created = client.post("/children", json={"name": "get-child-test"}).json()

    response = client.get(f"/children/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "get-child-test"
    assert body["current_streak"] == 0

    with SessionLocal() as db:
        db.query(Child).filter(Child.public_id == created["id"]).delete()
        db.commit()


def test_get_unknown_child_404s() -> None:
    response = client.get(f"/children/{uuid.uuid4()}")
    assert response.status_code == 404
