from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ChildOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProblemOut(BaseModel):
    attempt_id: int
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

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    access_token: str
    parent: ParentOut


class MasterySummary(BaseModel):
    skill_code: str
    difficulty: int
    rolling_accuracy: float | None
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
    id: int
    name: str
    mastery: list[MasterySummary]
    recent_attempts: list[AttemptSummary]
