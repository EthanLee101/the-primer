import pytest

from app.mastery import (
    MAX_DIFFICULTY,
    MAX_DIFFICULTY_STEP,
    MIN_DIFFICULTY,
    P_FORGET,
    P_GUESS,
    P_INIT,
    P_SLIP,
    P_TRANSIT,
    MasteryState,
    apply_attempt,
    difficulty_for,
    next_difficulty,
)


def test_fresh_state_starts_at_the_prior() -> None:
    state = MasteryState()
    assert state.p_know == P_INIT
    assert state.difficulty == MIN_DIFFICULTY


def test_one_correct_answer_matches_the_hand_computed_bayes_update() -> None:
    """Pins the update arithmetic itself, not just its qualitative shape.

    posterior = P(know)*P(correct|know) / [P(know)*P(correct|know) +
    P(not know)*P(correct|not know)]
              = (P_INIT * (1-P_SLIP)) / (P_INIT*(1-P_SLIP) + (1-P_INIT)*P_GUESS)
    then the transition step blends in learning/forgetting:
    p_know = posterior*(1-P_FORGET) + (1-posterior)*P_TRANSIT

    p_know itself is unaffected by difficulty pacing (see
    test_difficulty_moves_by_at_most_one_step_per_attempt) — only the
    difficulty derived from it is rate-limited, which is why this pins
    next_difficulty(...) rather than difficulty_for(...) directly.
    """
    joint_know = P_INIT * (1 - P_SLIP)
    joint_not_know = (1 - P_INIT) * P_GUESS
    expected_posterior = joint_know / (joint_know + joint_not_know)
    expected_p_know = expected_posterior * (1 - P_FORGET) + (1 - expected_posterior) * P_TRANSIT

    initial = MasteryState()
    state = apply_attempt(initial, correct=True)

    assert state.p_know == pytest.approx(expected_p_know)
    assert state.difficulty == next_difficulty(initial.difficulty, expected_p_know)


def test_difficulty_moves_by_at_most_one_step_per_attempt() -> None:
    """Regression test for the original design's biggest UX problem: a
    single attempt could swing difficulty by several levels at once (1 -> 4
    off one correct answer, later found to also allow 9 -> 2 off two wrong
    ones), because difficulty was read directly off p_know with no pacing.
    p_know is still free to swing however far the Bayesian math says —
    only the *served difficulty* is paced, one level at a time."""
    state = MasteryState()
    for correct in [True, True, True, False, False, True, False, False, False]:
        previous_difficulty = state.difficulty
        state = apply_attempt(state, correct=correct)
        assert abs(state.difficulty - previous_difficulty) <= MAX_DIFFICULTY_STEP


def test_p_know_stays_strictly_between_zero_and_one() -> None:
    state = MasteryState()
    for _ in range(50):
        state = apply_attempt(state, correct=True)
        assert 0.0 < state.p_know < 1.0
    for _ in range(50):
        state = apply_attempt(state, correct=False)
        assert 0.0 < state.p_know < 1.0


def test_difficulty_rises_after_sustained_correct_answers() -> None:
    state = MasteryState()
    for _ in range(6):
        state = apply_attempt(state, correct=True)
    assert state.difficulty > MIN_DIFFICULTY


def test_difficulty_falls_back_after_sustained_wrong_answers() -> None:
    """Vanilla BKT only models learning, so knowledge can never fall back
    down once observed — see the forgetting-parameter discussion in
    app/mastery.py. This is the regression test for that: without P_FORGET,
    difficulty would stay pinned at its post-streak peak forever. The wrong
    streak is longer than the correct one specifically because difficulty
    is now rate-limited (see test_difficulty_moves_by_at_most_one_step_per_attempt)
    — climbing down one level at a time from the peak genuinely takes more
    attempts than the belief itself needs to collapse."""
    state = MasteryState()
    for _ in range(6):
        state = apply_attempt(state, correct=True)
    peak_difficulty = state.difficulty
    assert peak_difficulty > MIN_DIFFICULTY

    for _ in range(8):
        state = apply_attempt(state, correct=False)
    assert state.difficulty < peak_difficulty
    assert state.difficulty == MIN_DIFFICULTY


def test_difficulty_never_exceeds_max() -> None:
    # P_FORGET fires on every attempt regardless of outcome, which caps the
    # achievable steady-state p_know below 1.0 (roughly 1 - P_FORGET) even
    # under an unbroken correct streak — so the real invariant to guard is
    # "never exceeds," not "reaches," the top of the band.
    state = MasteryState(difficulty=MAX_DIFFICULTY, p_know=1 - 1e-4)
    for _ in range(30):
        state = apply_attempt(state, correct=True)
        assert state.difficulty <= MAX_DIFFICULTY


def test_difficulty_never_drops_below_min() -> None:
    state = MasteryState(difficulty=MIN_DIFFICULTY, p_know=1e-4)
    for _ in range(30):
        state = apply_attempt(state, correct=False)
        assert state.difficulty >= MIN_DIFFICULTY


def test_attempts_and_correct_counts_accumulate() -> None:
    state = MasteryState()
    state = apply_attempt(state, correct=True)
    state = apply_attempt(state, correct=False)
    state = apply_attempt(state, correct=True)
    assert state.attempts_count == 3
    assert state.correct_count == 2


def test_difficulty_for_is_a_linear_map_across_the_full_band() -> None:
    assert difficulty_for(0.0) == MIN_DIFFICULTY
    assert difficulty_for(1.0) == MAX_DIFFICULTY
    assert MIN_DIFFICULTY <= difficulty_for(0.5) <= MAX_DIFFICULTY


def test_next_difficulty_clamps_to_the_valid_band_even_for_a_big_jump() -> None:
    assert next_difficulty(MIN_DIFFICULTY, p_know=1.0) == MIN_DIFFICULTY + MAX_DIFFICULTY_STEP
    assert next_difficulty(MAX_DIFFICULTY, p_know=0.0) == MAX_DIFFICULTY - MAX_DIFFICULTY_STEP
