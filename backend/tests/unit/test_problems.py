import pytest

from app.problems import Operation, generate_problem

SKILLS_BY_OPERATION = {
    "addition": Operation.ADD,
    "subtraction": Operation.SUBTRACT,
    "multiplication": Operation.MULTIPLY,
    "division": Operation.DIVIDE,
}


@pytest.mark.parametrize("skill_code", SKILLS_BY_OPERATION)
@pytest.mark.parametrize("difficulty", [1, 2, 5, 10])
def test_answer_is_correct(skill_code: str, difficulty: int) -> None:
    for _ in range(50):
        problem = generate_problem(skill_code, difficulty)
        assert problem.operation is SKILLS_BY_OPERATION[skill_code]
        assert problem.difficulty == difficulty
        a, b = problem.operand_a, problem.operand_b
        match problem.operation:
            case Operation.ADD:
                assert problem.answer == a + b
            case Operation.SUBTRACT:
                assert problem.answer == a - b
                assert problem.answer >= 0
            case Operation.MULTIPLY:
                assert problem.answer == a * b
            case Operation.DIVIDE:
                assert b != 0
                assert a % b == 0
                assert problem.answer == a // b


def test_prompt_formatting() -> None:
    problem = generate_problem("addition", 1)
    assert problem.prompt == f"{problem.operand_a} + {problem.operand_b}"


def test_unknown_skill_raises() -> None:
    with pytest.raises(ValueError, match="unknown skill code"):
        generate_problem("long_division_with_remainders", 1)


def test_invalid_difficulty_raises() -> None:
    with pytest.raises(ValueError, match="difficulty must be >= 1"):
        generate_problem("addition", 0)
