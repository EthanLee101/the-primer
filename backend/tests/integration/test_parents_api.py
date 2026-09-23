from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import Attempt, Child, Mastery, Parent

client = TestClient(app)


@pytest.fixture
def cleanup_emails() -> Iterator[list[str]]:
    emails: list[str] = []
    yield emails
    with SessionLocal() as db:
        for email in emails:
            parent = db.scalar(select(Parent).where(Parent.email == email.lower()))
            if parent is None:
                continue
            children = db.query(Child).filter(Child.parent_id == parent.id).all()
            for child in children:
                db.query(Attempt).filter(Attempt.child_id == child.id).delete()
                db.query(Mastery).filter(Mastery.child_id == child.id).delete()
            db.query(Child).filter(Child.parent_id == parent.id).delete()
            db.delete(parent)
            db.commit()


def test_register_creates_account_and_returns_session(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("ada@example.com")
    response = client.post(
        "/parents", json={"email": "ada@example.com", "password": "correct horse battery"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["parent"]["email"] == "ada@example.com"
    assert "access_token" in body
    assert "password" not in body["parent"]
    assert "password_hash" not in body["parent"]


def test_register_duplicate_email_is_rejected(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("dup@example.com")
    client.post("/parents", json={"email": "dup@example.com", "password": "correct horse battery"})
    response = client.post(
        "/parents", json={"email": "dup@example.com", "password": "a different password"}
    )
    assert response.status_code == 409


def test_register_rejects_short_password(cleanup_emails: list[str]) -> None:
    response = client.post("/parents", json={"email": "short@example.com", "password": "short"})
    assert response.status_code == 422


def test_register_rejects_invalid_email() -> None:
    response = client.post(
        "/parents", json={"email": "not-an-email", "password": "correct horse battery"}
    )
    assert response.status_code == 422


def test_login_with_correct_credentials(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("login@example.com")
    client.post(
        "/parents", json={"email": "login@example.com", "password": "correct horse battery"}
    )
    response = client.post(
        "/parents/login", json={"email": "login@example.com", "password": "correct horse battery"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_and_nonexistent_email_give_identical_responses(
    cleanup_emails: list[str],
) -> None:
    cleanup_emails.append("real@example.com")
    client.post("/parents", json={"email": "real@example.com", "password": "correct horse battery"})

    wrong_password = client.post(
        "/parents/login", json={"email": "real@example.com", "password": "totally wrong"}
    )
    no_such_account = client.post(
        "/parents/login", json={"email": "nobody@example.com", "password": "totally wrong"}
    )

    # identical status + body means the error message can't be used to
    # enumerate which emails have accounts
    assert wrong_password.status_code == no_such_account.status_code == 401
    assert wrong_password.json() == no_such_account.json()


def test_me_requires_authentication() -> None:
    response = client.get("/parents/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token() -> None:
    response = client.get("/parents/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_authenticated_parent(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("me@example.com")
    register = client.post(
        "/parents", json={"email": "me@example.com", "password": "correct horse battery"}
    )
    token = register.json()["access_token"]

    response = client.get("/parents/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_children_are_scoped_to_the_requesting_parent(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("parent-a@example.com")
    cleanup_emails.append("parent-b@example.com")

    reg_a = client.post(
        "/parents", json={"email": "parent-a@example.com", "password": "correct horse battery"}
    )
    reg_b = client.post(
        "/parents", json={"email": "parent-b@example.com", "password": "correct horse battery"}
    )
    token_a = reg_a.json()["access_token"]
    token_b = reg_b.json()["access_token"]

    # a child created while parent A is "logged in" (token sent) links to A
    client.post(
        "/children",
        json={"name": "kid-of-a"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    response_a = client.get("/parents/me/children", headers={"Authorization": f"Bearer {token_a}"})
    response_b = client.get("/parents/me/children", headers={"Authorization": f"Bearer {token_b}"})

    assert len(response_a.json()) == 1
    assert response_a.json()[0]["name"] == "kid-of-a"
    assert response_b.json() == []  # parent B must not see parent A's child


def test_child_creation_without_auth_still_works_and_is_unlinked() -> None:
    response = client.post("/children", json={"name": "anonymous-kid"})
    assert response.status_code == 201

    with SessionLocal() as db:
        child = db.get(Child, response.json()["id"])
        assert child is not None
        assert child.parent_id is None
        db.delete(child)
        db.commit()
