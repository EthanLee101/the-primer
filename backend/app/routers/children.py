import logging
import uuid
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.orm import Session

from app.auth import get_current_parent, get_current_parent_optional
from app.config import get_settings
from app.db import get_db
from app.mastery_repo import get_or_create_mastery
from app.models import Attempt, Child, Mastery, Parent, Skill
from app.problems import SKILL_OPERATIONS, generate_problem
from app.rate_limit import limiter
from app.schemas import ChildCreate, ChildOut, ProblemOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=ChildOut, status_code=201)
@limiter.limit(get_settings().general_rate_limit)
def create_child(
    request: Request,
    payload: ChildCreate,
    db: Session = Depends(get_db),
    parent: Parent | None = Depends(get_current_parent_optional),
) -> ChildOut:
    # no auth required — the child-facing flow (increments 6/7) stays
    # frictionless. If a parent session happens to be active (increment 10's
    # dashboard), the new child links to it; otherwise parent_id stays null.
    child = Child(name=payload.name, parent_id=parent.id if parent else None)
    db.add(child)
    db.commit()
    db.refresh(child)
    return ChildOut(
        id=child.public_id,
        name=child.name,
        created_at=child.created_at,
        current_streak=child.current_streak,
    )


@router.get("/{child_id}", response_model=ChildOut)
def get_child(child_id: uuid.UUID, db: Session = Depends(get_db)) -> ChildOut:
    """Unauthenticated, same as the other child-facing endpoints — see the
    Known gaps section in ARCHITECTURE.md for why. Exists so a returning
    child's localStorage-cached Child (which only reflects the state at
    the moment they last entered their name) picks up a fresh streak on
    load, without needing a login."""
    child = db.scalar(select(Child).where(Child.public_id == child_id))
    if child is None:
        raise HTTPException(status_code=404, detail="child not found")
    return ChildOut(
        id=child.public_id,
        name=child.name,
        created_at=child.created_at,
        current_streak=child.current_streak,
    )


@router.post("/{child_id}/claim", response_model=ChildOut)
def claim_child(
    child_id: uuid.UUID, parent: Parent = Depends(get_current_parent), db: Session = Depends(get_db)
) -> ChildOut:
    """Links an existing, previously-unowned child (e.g. one created before
    this parent had an account, or on this device by a kid playing solo) to
    the authenticated parent. A plain "SELECT then UPDATE if unowned" has the
    same race the increment-5 mastery bug had — two parents could both pass
    the check before either commits. This WHERE-conditioned UPDATE is atomic
    at the database level instead: at most one concurrent request can match
    parent_id IS NULL and actually update the row."""
    stmt = (
        update(Child)
        .where(Child.public_id == child_id, Child.parent_id.is_(None))
        .values(parent_id=parent.id)
    )
    result = cast("CursorResult[None]", db.execute(stmt))
    db.commit()

    child = db.scalar(select(Child).where(Child.public_id == child_id))
    if child is None:
        raise HTTPException(status_code=404, detail="child not found")
    if result.rowcount == 0 and child.parent_id != parent.id:
        # someone else already claimed it — not "already yours," a real conflict
        raise HTTPException(
            status_code=409, detail="This child is already linked to another account."
        )
    return ChildOut(
        id=child.public_id,
        name=child.name,
        created_at=child.created_at,
        current_streak=child.current_streak,
    )


@router.delete("/{child_id}", status_code=204)
def delete_child(
    child_id: uuid.UUID, parent: Parent = Depends(get_current_parent), db: Session = Depends(get_db)
) -> None:
    """A genuine delete, not an unlink — removing the parent_id link would
    leave the child's practice history orphaned in the database rather
    than actually cleaning it up. 404 uniformly for "doesn't exist" and
    "exists but isn't yours," rather than a 403/409 that would confirm to
    a non-owner that the child exists at all — same posture as claim_child
    distinguishing 404 from 409, just the other direction: here there's no
    legitimate reason for a non-owner to learn anything about a child that
    isn't theirs."""
    child = db.scalar(
        select(Child).where(Child.public_id == child_id, Child.parent_id == parent.id)
    )
    if child is None:
        raise HTTPException(status_code=404, detail="child not found")

    db.execute(delete(Attempt).where(Attempt.child_id == child.id))
    db.execute(delete(Mastery).where(Mastery.child_id == child.id))
    db.delete(child)
    db.commit()


@router.post("/{child_id}/problems", response_model=ProblemOut, status_code=201)
@limiter.limit(get_settings().general_rate_limit)
def create_problem(
    request: Request, child_id: uuid.UUID, skill: str, db: Session = Depends(get_db)
) -> ProblemOut:
    if skill not in SKILL_OPERATIONS:
        raise HTTPException(status_code=400, detail=f"unknown skill: {skill}")

    child = db.scalar(select(Child).where(Child.public_id == child_id))
    if child is None:
        raise HTTPException(status_code=404, detail="child not found")

    skill_row = db.scalar(select(Skill).where(Skill.code == skill))
    if skill_row is None:
        # a skill recognized by SKILL_OPERATIONS but missing its seeded row is
        # a data consistency bug, not something to expose to the client
        logger.error("skill '%s' is a known skill code but has no seeded row", skill)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    mastery = get_or_create_mastery(db, child.id, skill_row.id)
    problem = generate_problem(skill, mastery.difficulty)

    # store the operands server-side now; grading later happens against these,
    # never against values a client could send back at answer time
    attempt = Attempt(
        child_id=child.id,
        skill_id=skill_row.id,
        difficulty=problem.difficulty,
        operand_a=problem.operand_a,
        operand_b=problem.operand_b,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return ProblemOut(
        attempt_id=attempt.public_id,
        skill_code=skill,
        difficulty=problem.difficulty,
        operand_a=problem.operand_a,
        operand_b=problem.operand_b,
        prompt=problem.prompt,
    )
