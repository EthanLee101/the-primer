import uuid
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
        child = db.scalar(select(Child).where(Child.public_id == response.json()["id"]))
        assert child is not None
        assert child.parent_id is None
        db.delete(child)
        db.commit()


def test_claim_links_an_unowned_child(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("claimer@example.com")
    anon = client.post("/children", json={"name": "solo-kid"})
    child_id = anon.json()["id"]

    reg = client.post(
        "/parents", json={"email": "claimer@example.com", "password": "correct horse battery"}
    )
    token = reg.json()["access_token"]

    response = client.post(
        f"/children/{child_id}/claim", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == child_id

    dashboard = client.get("/parents/me/children", headers={"Authorization": f"Bearer {token}"})
    assert any(c["id"] == child_id for c in dashboard.json())


def test_claim_is_idempotent_for_the_same_parent(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("reclaimer@example.com")
    anon = client.post("/children", json={"name": "solo-kid-2"})
    child_id = anon.json()["id"]

    reg = client.post(
        "/parents", json={"email": "reclaimer@example.com", "password": "correct horse battery"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(f"/children/{child_id}/claim", headers=headers)
    second = client.post(f"/children/{child_id}/claim", headers=headers)
    assert first.status_code == second.status_code == 200


def test_claim_rejects_a_child_already_owned_by_another_parent(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("owner@example.com")
    cleanup_emails.append("rival@example.com")
    anon = client.post("/children", json={"name": "contested-kid"})
    child_id = anon.json()["id"]

    owner_token = client.post(
        "/parents", json={"email": "owner@example.com", "password": "correct horse battery"}
    ).json()["access_token"]
    rival_token = client.post(
        "/parents", json={"email": "rival@example.com", "password": "correct horse battery"}
    ).json()["access_token"]

    client.post(f"/children/{child_id}/claim", headers={"Authorization": f"Bearer {owner_token}"})
    response = client.post(
        f"/children/{child_id}/claim", headers={"Authorization": f"Bearer {rival_token}"}
    )
    assert response.status_code == 409


def test_claim_requires_authentication() -> None:
    anon = client.post("/children", json={"name": "unauthenticated-claim-target"})
    response = client.post(f"/children/{anon.json()['id']}/claim")
    assert response.status_code == 401

    with SessionLocal() as db:
        child = db.scalar(select(Child).where(Child.public_id == anon.json()["id"]))
        assert child is not None
        db.delete(child)
        db.commit()


def test_claim_nonexistent_child_404s(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("claim-404@example.com")
    token = client.post(
        "/parents", json={"email": "claim-404@example.com", "password": "correct horse battery"}
    ).json()["access_token"]

    response = client.post(
        f"/children/{uuid.uuid4()}/claim", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_recent_attempts_excludes_unanswered_ones(cleanup_emails: list[str]) -> None:
    """Regression test: a served-but-never-answered attempt (correct=None,
    answered_at=None) showed up in a real browser session — React
    StrictMode's double-effect-fire in dev creates two "serve a problem"
    requests, and the client only ever displays/answers one, but the server
    had already committed both. The dashboard used to show the unanswered
    one as a false "wrong answer" (a naive `correct ? right : wrong` display
    treats None the same as False). Confirmed with real data via direct DB
    inspection before fixing."""
    cleanup_emails.append("unanswered@example.com")
    token = client.post(
        "/parents", json={"email": "unanswered@example.com", "password": "correct horse battery"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    child_id = client.post(
        "/children", json={"name": "kid"}, headers=headers
    ).json()["id"]

    # one answered attempt
    answered = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    client.post(
        f"/attempts/{answered['attempt_id']}/answer",
        json={"submitted_answer": answered["operand_a"] + answered["operand_b"]},
    )
    # one served but never answered — simulates the StrictMode double-fire
    client.post(f"/children/{child_id}/problems", params={"skill": "addition"})

    dashboard = client.get("/parents/me/children", headers=headers).json()
    recent = dashboard[0]["recent_attempts"]
    assert len(recent) == 1
    assert all(a["correct"] is not None for a in recent)


def test_deleting_own_child_removes_it_and_its_data(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("deleter@example.com")
    token = client.post(
        "/parents", json={"email": "deleter@example.com", "password": "correct horse battery"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    child_id = client.post("/children", json={"name": "to-delete"}, headers=headers).json()["id"]
    problem = client.post(f"/children/{child_id}/problems", params={"skill": "addition"}).json()
    client.post(
        f"/attempts/{problem['attempt_id']}/answer",
        json={"submitted_answer": problem["operand_a"] + problem["operand_b"]},
    )

    response = client.delete(f"/children/{child_id}", headers=headers)
    assert response.status_code == 204

    dashboard = client.get("/parents/me/children", headers=headers).json()
    assert dashboard == []


def test_deleting_another_parents_child_404s(cleanup_emails: list[str]) -> None:
    cleanup_emails.append("child-owner@example.com")
    cleanup_emails.append("not-the-owner@example.com")
    owner_token = client.post(
        "/parents", json={"email": "child-owner@example.com", "password": "correct horse battery"}
    ).json()["access_token"]
    other_token = client.post(
        "/parents",
        json={"email": "not-the-owner@example.com", "password": "correct horse battery"},
    ).json()["access_token"]

    child_id = client.post(
        "/children", json={"name": "not-yours"}, headers={"Authorization": f"Bearer {owner_token}"}
    ).json()["id"]

    response = client.delete(
        f"/children/{child_id}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert response.status_code == 404

    # still there for the actual owner
    dashboard = client.get(
        "/parents/me/children", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    assert len(dashboard) == 1
