"""Bayesian Knowledge Tracing mastery tracking.

Tracks p_know: the estimated probability a child has mastered a skill,
given everything observed about them on it so far. Each attempt updates
this belief in two steps:

1. A Bayesian posterior update from the observed result. A correct answer
   is evidence for "knows it," but not proof (they could have guessed); a
   wrong answer is evidence against, but not proof either (they could have
   slipped on something they know). p_slip/p_guess calibrate how strong
   that evidence is.
2. A transition step modeling how mastery changes over time: some chance
   of having learned it just now if they didn't know it (p_transit), and —
   the one deliberate departure from textbook BKT (Corbett & Anderson,
   1994) — some chance of having forgotten it if they did (p_forget).
   Vanilla BKT only models learning, never forgetting, because it was
   designed to answer "has this student mastered the skill yet," where
   mastery is treated as sticky once reached. This product needs the
   opposite: difficulty has to track a child's *current* performance and
   come back down if they start missing problems, so a pure "knowledge
   only ever goes up" model isn't good enough here — without forgetting,
   p_know saturates near 1.0 after a short correct streak and gets stuck
   there (floating point rounds `1 - p_know` to exactly 0), and no amount
   of subsequent wrong answers can move it. p_forget fixes that.

Difficulty is a linear function of p_know across MIN_DIFFICULTY..MAX_DIFFICULTY,
rate-limited to move at most MAX_DIFFICULTY_STEP levels per attempt (see
next_difficulty). p_know itself is never rate-limited — it's free to swing
however far the Bayesian math says a single observation warrants, since
that's a genuine belief update, not a UX decision. But a single wrong
answer legitimately cratering the belief from "probably knows this" to
"probably doesn't" is not the same thing as it being reasonable to hand a
child a five-level-easier problem on the very next question — the model's
confidence and the child's felt experience of difficulty are two different
concerns, and conflating them is what made the first version of this file
feel jarring (1 -> 4 off a single correct answer, 9 -> 2 off two wrong
ones). Rate-limiting the output, not the belief, keeps the model itself
honest while keeping the pacing a child actually experiences gradual —
the same one-level-at-a-time cadence the original v1 rules engine used.

The four BKT constants below are engineering-tuned starting points (picked
by simulating attempt sequences until the resulting difficulty curve was
smooth and well-behaved — see tests/unit/test_mastery.py), not values fit
from real usage data. A production system would fit these per skill via EM
on logged attempts once there's enough data to do that meaningfully.

Kept DB-free and pure, like the v1 rolling-accuracy engine it replaces, so
the update math can be tested and reasoned about on its own — same
separation used in problems.py.
"""

from dataclasses import dataclass

INITIAL_DIFFICULTY = 1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 10

# Prior probability a child already knows a skill before their first
# attempt at it. Low, not zero — BKT treats "no evidence yet" as "probably
# doesn't know it" rather than a hard 0, which is what lets a single lucky
# guess move p_know without the math breaking down (a literal 0 prior can
# only be updated by Bayes' rule if the evidence has non-zero probability
# under it, which a guess does).
P_INIT = 0.05

# Probability of learning the skill from a single practice opportunity,
# applied to the "doesn't know" share after each attempt's evidence update.
P_TRANSIT = 0.02

# Probability of forgetting the skill since the last attempt, applied to
# the "knows" share after each attempt's evidence update. This fires on
# every attempt (right or wrong) — which means it also caps how high
# p_know can climb under a pure correct streak, at roughly 1 - P_FORGET.
# Kept small for that reason (a long correct streak should be able to
# reach the top of the difficulty band), but not zero: a small constant
# rate is what breaks the floating-point lock-in described above, and it's
# what makes a wrong-answer streak able to pull difficulty back down
# quickly (see the module docstring). Below P_TRANSIT would let a single
# early streak of luck matter more than it should; this is comfortably
# above it instead.
P_FORGET = 0.05

# P(wrong answer | actually knows the skill) — an arithmetic slip, not a
# knowledge gap.
P_SLIP = 0.1

# P(right answer | doesn't actually know the skill). These are free-
# response numeric answers, not multiple choice, so blind guessing rarely
# lands on the exact right number — kept low, not the ~0.25 a 4-option
# multiple-choice BKT model would use.
P_GUESS = 0.1

# The most a served difficulty can move, up or down, from one attempt to
# the next — regardless of how far p_know itself just moved. See the
# module docstring for why this is separate from the BKT math.
MAX_DIFFICULTY_STEP = 1

# p_know is kept strictly inside (0, 1) after every update. Bayes' rule
# alone can drive it to exactly 0.0 or 1.0 in floating point once the
# "unlikely" side underflows — and once it's exactly 0 or 1, no further
# evidence can ever move it again (multiplying by it always keeps it
# there). This epsilon keeps every future update mathematically able to
# respond to new evidence, in either direction.
_EPSILON = 1e-4


@dataclass(frozen=True)
class MasteryState:
    difficulty: int = INITIAL_DIFFICULTY
    p_know: float = P_INIT
    attempts_count: int = 0
    correct_count: int = 0


def difficulty_for(p_know: float) -> int:
    """Linear map from mastery probability to the difficulty band — what
    difficulty would fully reflect this belief, with no pacing applied."""
    span = MAX_DIFFICULTY - MIN_DIFFICULTY
    return MIN_DIFFICULTY + round(p_know * span)


def next_difficulty(previous_difficulty: int, p_know: float) -> int:
    """What difficulty to actually serve next: difficulty_for(p_know),
    clamped to move at most MAX_DIFFICULTY_STEP from previous_difficulty."""
    target = difficulty_for(p_know)
    step = max(-MAX_DIFFICULTY_STEP, min(MAX_DIFFICULTY_STEP, target - previous_difficulty))
    return min(max(previous_difficulty + step, MIN_DIFFICULTY), MAX_DIFFICULTY)


def apply_attempt(state: MasteryState, correct: bool) -> MasteryState:
    # Step 1: Bayesian posterior update from the observed evidence.
    # P(evidence | knows) vs P(evidence | doesn't know), combined with the
    # prior via Bayes' rule: posterior = P(know, evidence) / P(evidence).
    if correct:
        p_evidence_given_know = 1 - P_SLIP
        p_evidence_given_not_know = P_GUESS
    else:
        p_evidence_given_know = P_SLIP
        p_evidence_given_not_know = 1 - P_GUESS

    prior = state.p_know
    joint_know = prior * p_evidence_given_know
    joint_not_know = (1 - prior) * p_evidence_given_not_know
    posterior = joint_know / (joint_know + joint_not_know)

    # Step 2: transition — some chance of having learned it if they didn't
    # know it, some chance of having forgotten it if they did.
    p_know = posterior * (1 - P_FORGET) + (1 - posterior) * P_TRANSIT
    p_know = min(max(p_know, _EPSILON), 1 - _EPSILON)

    attempts_count = state.attempts_count + 1
    correct_count = state.correct_count + (1 if correct else 0)

    return MasteryState(
        difficulty=next_difficulty(state.difficulty, p_know),
        p_know=p_know,
        attempts_count=attempts_count,
        correct_count=correct_count,
    )
