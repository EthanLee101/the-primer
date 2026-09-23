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
        return format_prompt(self.operand_a, self.operand_b, self.operation)


def format_prompt(operand_a: int, operand_b: int, operation: Operation) -> str:
    symbol = _OPERATION_SYMBOLS[operation]
    return f"{operand_a} {symbol} {operand_b}"


def grade(operand_a: int, operand_b: int, operation: Operation) -> int:
    """The single source of truth for what's correct — used both when a problem
    is generated and, unchanged, when a submitted answer is checked against
    whatever operands were actually stored for that attempt."""
    match operation:
        case Operation.ADD:
            return operand_a + operand_b
        case Operation.SUBTRACT:
            return operand_a - operand_b
        case Operation.MULTIPLY:
            return operand_a * operand_b
        case Operation.DIVIDE:
            return operand_a // operand_b


def generate_problem(skill_code: str, difficulty: int) -> Problem:
    if difficulty < 1:
        raise ValueError("difficulty must be >= 1")
    operation = SKILL_OPERATIONS.get(skill_code)
    if operation is None:
        raise ValueError(f"unknown skill code: {skill_code}")

    if operation is Operation.SUBTRACT:
        a, b = _random_pair(difficulty)
        a, b = max(a, b), min(a, b)  # keep results non-negative for young learners
    elif operation is Operation.ADD:
        a, b = _random_pair(difficulty)
    else:  # MULTIPLY or DIVIDE
        divisor, quotient = _random_factor_pair(difficulty)
        if operation is Operation.DIVIDE:
            a, b = divisor * quotient, divisor  # always divides evenly
        else:
            a, b = divisor, quotient

    return Problem(skill_code, difficulty, a, b, operation, grade(a, b, operation))


def _random_pair(difficulty: int) -> tuple[int, int]:
    upper = min(9 * difficulty, 999)
    return random.randint(1, upper), random.randint(1, upper)


def _random_factor_pair(difficulty: int) -> tuple[int, int]:
    # multiplication/division blow up fast, so scale these more gently than +/-
    upper = min(2 + difficulty, 12)
    return random.randint(1, upper), random.randint(1, upper)
