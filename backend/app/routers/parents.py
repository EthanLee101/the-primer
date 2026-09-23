from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_session_token, get_current_parent, hash_password, verify_password
from app.config import get_settings
from app.db import get_db
from app.models import Attempt, Child, Mastery, Parent
from app.rate_limit import limiter
from app.schemas import (
    AttemptSummary,
    ChildProgress,
    MasterySummary,
    ParentCredentials,
    ParentOut,
    SessionOut,
)

router = APIRouter(prefix="/parents", tags=["parents"])


@router.post("", response_model=SessionOut, status_code=201)
@limiter.limit(get_settings().auth_rate_limit)
def register(
    request: Request, payload: ParentCredentials, db: Session = Depends(get_db)
) -> SessionOut:
    parent = Parent(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(parent)
    try:
        db.commit()
    except IntegrityError:
        # SELECT-then-INSERT here would have the same race the mastery bug
        # had — catching the DB's own unique constraint is race-safe
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from None
    db.refresh(parent)
    token = create_session_token(parent.id)
    return SessionOut(access_token=token, parent=ParentOut.model_validate(parent))


@router.post("/login", response_model=SessionOut)
@limiter.limit(get_settings().auth_rate_limit)
def login(
    request: Request, payload: ParentCredentials, db: Session = Depends(get_db)
) -> SessionOut:
    parent = db.scalar(select(Parent).where(Parent.email == payload.email.lower()))
    # always verify, even when parent is None — keeps response timing (and
    # the error message below) identical whether the email exists or not
    if not verify_password(payload.password, parent.password_hash if parent else None):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    assert parent is not None  # verify_password only returns True for a real parent
    token = create_session_token(parent.id)
    return SessionOut(access_token=token, parent=ParentOut.model_validate(parent))


@router.get("/me", response_model=ParentOut)
def me(parent: Parent = Depends(get_current_parent)) -> Parent:
    return parent


@router.get("/me/children", response_model=list[ChildProgress])
def my_children(
    parent: Parent = Depends(get_current_parent), db: Session = Depends(get_db)
) -> list[ChildProgress]:
    children = db.scalars(select(Child).where(Child.parent_id == parent.id)).all()

    result = []
    for child in children:
        masteries = db.scalars(select(Mastery).where(Mastery.child_id == child.id)).all()
        recent = db.scalars(
            select(Attempt)
            # answered only — a served-but-never-answered attempt (a child
            # switches skills mid-problem, closes the tab, or — in dev —
            # React StrictMode double-firing the "serve a problem" effect)
            # has correct=None, which a naive "correct ? right : wrong"
            # display would show as a false "wrong answer." Confirmed live:
            # StrictMode's double effect really does create two Attempt rows
            # server-side even though the client only ever displays one.
            .where(Attempt.child_id == child.id, Attempt.answered_at.is_not(None))
            .order_by(Attempt.created_at.desc())
            .limit(10)
        ).all()
        result.append(
            ChildProgress(
                id=child.id,
                name=child.name,
                mastery=[
                    MasterySummary(
                        skill_code=m.skill.code,
                        difficulty=m.difficulty,
                        rolling_accuracy=m.rolling_accuracy,
                        attempts_count=m.attempts_count,
                        correct_count=m.correct_count,
                    )
                    for m in masteries
                ],
                recent_attempts=[
                    AttemptSummary(
                        skill_code=a.skill.code,
                        difficulty=a.difficulty,
                        correct=a.correct,
                        created_at=a.created_at,
                    )
                    for a in recent
                ],
            )
        )
    return result
