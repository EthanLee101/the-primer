"""Rules-based mastery/difficulty tracking.

Deliberately simple and transparent for v1 — increment 11 upgrades this to
Bayesian Knowledge Tracing. Kept DB-free and pure so the adjustment logic can
be tested and reasoned about on its own, the same separation used in
problems.py.
"""

from dataclasses import dataclass

INITIAL_DIFFICULTY = 1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 10

# recent attempts count more than old ones (exponential moving average),
# rather than weighting a child's very first attempt equally with their 50th
ROLLING_ACCURACY_ALPHA = 0.3

PROMOTE_THRESHOLD = 0.8
DEMOTE_THRESHOLD = 0.4
# require a few data points before moving difficulty off a single lucky/unlucky answer
MIN_ATTEMPTS_BEFORE_ADJUST = 3


@dataclass(frozen=True)
class MasteryState:
    difficulty: int = INITIAL_DIFFICULTY
    rolling_accuracy: float | None = None
    attempts_count: int = 0
    correct_count: int = 0


def apply_attempt(state: MasteryState, correct: bool) -> MasteryState:
    observed = 1.0 if correct else 0.0
    rolling_accuracy = (
        observed
        if state.rolling_accuracy is None
        else ROLLING_ACCURACY_ALPHA * observed
        + (1 - ROLLING_ACCURACY_ALPHA) * state.rolling_accuracy
    )
    attempts_count = state.attempts_count + 1
    correct_count = state.correct_count + (1 if correct else 0)

    difficulty = state.difficulty
    if attempts_count >= MIN_ATTEMPTS_BEFORE_ADJUST:
        if rolling_accuracy >= PROMOTE_THRESHOLD:
            difficulty = min(state.difficulty + 1, MAX_DIFFICULTY)
        elif rolling_accuracy <= DEMOTE_THRESHOLD:
            difficulty = max(state.difficulty - 1, MIN_DIFFICULTY)

    return MasteryState(
        difficulty=difficulty,
        rolling_accuracy=rolling_accuracy,
        attempts_count=attempts_count,
        correct_count=correct_count,
    )
