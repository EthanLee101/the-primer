import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.llm import generate_explanation
from app.mastery import apply_attempt
from app.mastery_repo import apply_state, get_or_create_mastery, to_state
from app.models import Attempt
from app.problems import SKILL_OPERATIONS, format_prompt, grade
from app.rate_limit import limiter
from app.schemas import AnswerResult, AnswerSubmit
from app.streak import StreakState, update_streak

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/{attempt_id}/answer", response_model=AnswerResult)
@limiter.limit(get_settings().answer_rate_limit)
def submit_answer(
    request: Request,
    attempt_id: uuid.UUID,
    payload: AnswerSubmit,
    db: Session = Depends(get_db),
) -> AnswerResult:
    attempt = db.scalar(select(Attempt).where(Attempt.public_id == attempt_id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="attempt not found")
    if attempt.answered_at is not None:
        raise HTTPException(status_code=409, detail="attempt already answered")

    operation = SKILL_OPERATIONS.get(attempt.skill.code)
    if operation is None:
        # a seeded skill row with a code we don't recognize is a data
        # consistency bug, not something to expose to the client
        logger.error("attempt %s has unrecognized skill code: %s", attempt_id, attempt.skill.code)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    correct_answer = grade(attempt.operand_a, attempt.operand_b, operation)
    is_correct = payload.submitted_answer == correct_answer

    attempt.submitted_answer = payload.submitted_answer
    attempt.correct = is_correct
    attempt.answered_at = datetime.now(UTC)

    mastery = get_or_create_mastery(db, attempt.child_id, attempt.skill_id)
    apply_state(mastery, apply_attempt(to_state(mastery), is_correct))

    # streak counts a day practiced, not a day answered correctly — updates
    # regardless of is_correct, same trigger point as the mastery update above
    streak = update_streak(
        StreakState(attempt.child.current_streak, attempt.child.last_practice_date),
        datetime.now(UTC).date(),
    )
    attempt.child.current_streak = streak.current_streak
    attempt.child.last_practice_date = streak.last_practice_date

    db.commit()

    explanation = None
    if not is_correct:
        prompt = format_prompt(attempt.operand_a, attempt.operand_b, operation)
        explanation = generate_explanation(prompt, payload.submitted_answer, correct_answer)

    return AnswerResult(correct=is_correct, correct_answer=correct_answer, explanation=explanation)
