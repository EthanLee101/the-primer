from datetime import datetime

from pydantic import BaseModel, Field


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
