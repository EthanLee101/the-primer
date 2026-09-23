import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.mastery_repo import get_or_create_mastery
from app.models import Attempt, Child, Skill
from app.problems import SKILL_OPERATIONS, generate_problem
from app.schemas import ChildCreate, ChildOut, ProblemOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=ChildOut, status_code=201)
def create_child(payload: ChildCreate, db: Session = Depends(get_db)) -> Child:
    child = Child(name=payload.name)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.post("/{child_id}/problems", response_model=ProblemOut, status_code=201)
def create_problem(child_id: int, skill: str, db: Session = Depends(get_db)) -> ProblemOut:
    if skill not in SKILL_OPERATIONS:
        raise HTTPException(status_code=400, detail=f"unknown skill: {skill}")

    child = db.get(Child, child_id)
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
        attempt_id=attempt.id,
        skill_code=skill,
        difficulty=problem.difficulty,
        operand_a=problem.operand_a,
        operand_b=problem.operand_b,
        prompt=problem.prompt,
    )
