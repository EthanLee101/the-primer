"""Deterministic arithmetic problem generation.

Grading here is pure arithmetic, not model-judged — the LLM layer (increment 8)
only handles explanations for wrong answers, never correctness itself.
"""

import random
from dataclasses import dataclass
from enum import StrEnum


class Operation(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


_OPERATION_SYMBOLS = {
    Operation.ADD: "+",
    Operation.SUBTRACT: "-",
    Operation.MULTIPLY: "×",
    Operation.DIVIDE: "÷",
}

# skill code (as stored in the `skill` table) -> operation it drills
SKILL_OPERATIONS: dict[str, Operation] = {
    "addition": Operation.ADD,
    "subtraction": Operation.SUBTRACT,
    "multiplication": Operation.MULTIPLY,
    "division": Operation.DIVIDE,
}


@dataclass(frozen=True)
class Problem:
    skill_code: str
    difficulty: int
    operand_a: int
    operand_b: int
    operation: Operation
    answer: int

    @property
    def prompt(self) -> str:
        symbol = _OPERATION_SYMBOLS[self.operation]
        return f"{self.operand_a} {symbol} {self.operand_b}"


def generate_problem(skill_code: str, difficulty: int) -> Problem:
    if difficulty < 1:
        raise ValueError("difficulty must be >= 1")
    operation = SKILL_OPERATIONS.get(skill_code)
    if operation is None:
        raise ValueError(f"unknown skill code: {skill_code}")

    if operation is Operation.ADD:
        a, b = _random_pair(difficulty)
        answer = a + b
    elif operation is Operation.SUBTRACT:
        a, b = _random_pair(difficulty)
        a, b = max(a, b), min(a, b)  # keep results non-negative for young learners
        answer = a - b
    elif operation is Operation.MULTIPLY:
        a, b = _random_factor_pair(difficulty)
        answer = a * b
    else:  # DIVIDE
        divisor, quotient = _random_factor_pair(difficulty)
        a, b = divisor * quotient, divisor  # always divides evenly
        answer = quotient

    return Problem(skill_code, difficulty, a, b, operation, answer)


def _random_pair(difficulty: int) -> tuple[int, int]:
    upper = min(9 * difficulty, 999)
    return random.randint(1, upper), random.randint(1, upper)


def _random_factor_pair(difficulty: int) -> tuple[int, int]:
    # multiplication/division blow up fast, so scale these more gently than +/-
    upper = min(2 + difficulty, 12)
    return random.randint(1, upper), random.randint(1, upper)
