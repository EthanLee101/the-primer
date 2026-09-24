"""Return/streak tracking — consecutive calendar days a child has answered
at least one attempt. Kept DB-free and pure, same separation as
app/mastery.py and app/problems.py: this module only knows how to compute
the next (streak, last_practice_date) pair from an old one plus today's
date, never how that state gets persisted.

Calendar-day granularity, keyed off naive UTC (datetime.now(UTC).date()),
matching the convention app/routers/attempts.py already uses for
answered_at. No per-child timezone is stored anywhere in this app, so
there's no more-correct "midnight" to use even if we wanted one — a known,
deliberate simplification, not a new gap (see ARCHITECTURE.md Known gaps).
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StreakState:
    current_streak: int = 0
    last_practice_date: date | None = None


def update_streak(state: StreakState, today: date) -> StreakState:
    if state.last_practice_date == today:
        return state  # already counted today — a second attempt shouldn't double-increment
    if state.last_practice_date is not None and (today - state.last_practice_date).days == 1:
        return StreakState(current_streak=state.current_streak + 1, last_practice_date=today)
    # first-ever practice, or a gap of 2+ days — starts over at 1
    return StreakState(current_streak=1, last_practice_date=today)
