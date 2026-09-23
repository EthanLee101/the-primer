from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.mastery import apply_attempt
from app.mastery_repo import apply_state, get_or_create_mastery, to_state
from app.models import Attempt
from app.problems import SKILL_OPERATIONS, grade
from app.schemas import AnswerResult, AnswerSubmit

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/{attempt_id}/answer", response_model=AnswerResult)
def submit_answer(
    attempt_id: int, payload: AnswerSubmit, db: Session = Depends(get_db)
) -> AnswerResult:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="attempt not found")
    if attempt.answered_at is not None:
        raise HTTPException(status_code=409, detail="attempt already answered")

    operation = SKILL_OPERATIONS.get(attempt.skill.code)
    if operation is None:
        raise HTTPException(status_code=500, detail=f"unrecognized skill: {attempt.skill.code}")

    correct_answer = grade(attempt.operand_a, attempt.operand_b, operation)
    is_correct = payload.submitted_answer == correct_answer

    attempt.submitted_answer = payload.submitted_answer
    attempt.correct = is_correct
    attempt.answered_at = datetime.now(UTC)

    mastery = get_or_create_mastery(db, attempt.child_id, attempt.skill_id)
    apply_state(mastery, apply_attempt(to_state(mastery), is_correct))

    db.commit()

    return AnswerResult(correct=is_correct, correct_answer=correct_answer)
