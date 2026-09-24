import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ChildOut(BaseModel):
    # This is Child.public_id, never the internal int PK — see the
    # comment on Child.public_id in app/models.py. Always constructed
    # explicitly in the router (id=child.public_id), not via
    # from_attributes, since a field named "id" would otherwise silently
    # pick up the wrong attribute by name.
    id: uuid.UUID
    name: str
    created_at: datetime
    current_streak: int


class ProblemOut(BaseModel):
    attempt_id: uuid.UUID
    skill_code: str
    difficulty: int
    operand_a: int
    operand_b: int
    prompt: str


class AnswerSubmit(BaseModel):
    submitted_answer: int


class AnswerResult(BaseModel):
    correct: bool
    correct_answer: int
    # only ever set on a wrong answer; None if correct, or if the LLM call
    # failed (a missing explanation is never itself an error — see app/llm.py)
    explanation: str | None = None


class ParentCredentials(BaseModel):
    email: EmailStr
    # NIST 800-63B: length beats forced complexity rules. 100 is a sanity
    # cap, not a security control — just avoids hashing arbitrarily huge input.
    password: str = Field(min_length=8, max_length=100)


class ParentOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    has_pin: bool

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    access_token: str
    parent: ParentOut


class PinSet(BaseModel):
    # 4-6 digit numeric PIN, kept as a string (not int) — leading zeros are
    # valid and nothing ever does arithmetic on it. The regex is a format
    # guard only; the small keyspace is defended by pin-login's rate limit,
    # not by format strictness.
    pin: str = Field(pattern=r"^\d{4,6}$")


class PinLogin(BaseModel):
    email: EmailStr
    pin: str = Field(pattern=r"^\d{4,6}$")


class MasterySummary(BaseModel):
    skill_code: str
    difficulty: int
    p_know: float
    attempts_count: int
    correct_count: int


class AttemptSummary(BaseModel):
    # skill_code comes from attempt.skill.code, not a direct Attempt column —
    # built explicitly in the router, not via from_attributes
    skill_code: str
    difficulty: int
    correct: bool | None
    created_at: datetime


class ChildProgress(BaseModel):
    id: uuid.UUID
    name: str
    mastery: list[MasterySummary]
    recent_attempts: list[AttemptSummary]
