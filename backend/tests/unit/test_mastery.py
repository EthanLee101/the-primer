from app.mastery import (
    DEMOTE_THRESHOLD,
    MAX_DIFFICULTY,
    MIN_ATTEMPTS_BEFORE_ADJUST,
    MIN_DIFFICULTY,
    MasteryState,
    apply_attempt,
)


def test_difficulty_holds_below_minimum_attempt_gate() -> None:
    state = MasteryState()
    for _ in range(MIN_ATTEMPTS_BEFORE_ADJUST - 1):
        state = apply_attempt(state, correct=True)
    assert state.difficulty == MasteryState().difficulty


def test_difficulty_increases_after_sustained_correct_answers() -> None:
    state = MasteryState()
    for _ in range(10):
        state = apply_attempt(state, correct=True)
    assert state.difficulty > MasteryState().difficulty
    assert state.rolling_accuracy is not None
    assert state.rolling_accuracy > 0.9


def test_difficulty_decreases_after_sustained_wrong_answers() -> None:
    state = MasteryState(difficulty=5)
    for _ in range(10):
        state = apply_attempt(state, correct=False)
    assert state.difficulty < 5
    assert state.rolling_accuracy is not None
    assert state.rolling_accuracy < DEMOTE_THRESHOLD


def test_difficulty_never_exceeds_max() -> None:
    state = MasteryState(difficulty=MAX_DIFFICULTY)
    for _ in range(20):
        state = apply_attempt(state, correct=True)
    assert state.difficulty == MAX_DIFFICULTY


def test_difficulty_never_drops_below_min() -> None:
    state = MasteryState(difficulty=MIN_DIFFICULTY)
    for _ in range(20):
        state = apply_attempt(state, correct=False)
    assert state.difficulty == MIN_DIFFICULTY


def test_attempts_and_correct_counts_accumulate() -> None:
    state = MasteryState()
    state = apply_attempt(state, correct=True)
    state = apply_attempt(state, correct=False)
    state = apply_attempt(state, correct=True)
    assert state.attempts_count == 3
    assert state.correct_count == 2


def test_mixed_results_hold_difficulty_steady() -> None:
    state = MasteryState()
    for _ in range(20):
        state = apply_attempt(state, correct=True)
        state = apply_attempt(state, correct=False)
    assert state.difficulty == MasteryState().difficulty
