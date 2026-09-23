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
