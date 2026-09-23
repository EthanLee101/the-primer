from fastapi.testclient import TestClient

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

    with SessionLocal() as db:
        db.query(Child).filter(Child.id == body["id"]).delete()
        db.commit()


def test_create_child_rejects_empty_name() -> None:
    response = client.post("/children", json={"name": ""})
    assert response.status_code == 422
