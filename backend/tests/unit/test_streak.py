from datetime import date, timedelta

from app.streak import StreakState, update_streak

DAY1 = date(2026, 1, 1)


def test_first_ever_practice_starts_a_one_day_streak() -> None:
    state = update_streak(StreakState(), DAY1)
    assert state.current_streak == 1
    assert state.last_practice_date == DAY1


def test_a_second_attempt_the_same_day_does_not_double_increment() -> None:
    state = update_streak(StreakState(), DAY1)
    state = update_streak(state, DAY1)
    assert state.current_streak == 1
    assert state.last_practice_date == DAY1


def test_practicing_the_very_next_day_increments_the_streak() -> None:
    state = update_streak(StreakState(), DAY1)
    state = update_streak(state, DAY1 + timedelta(days=1))
    assert state.current_streak == 2


def test_a_gap_of_two_or_more_days_resets_the_streak_to_one() -> None:
    state = update_streak(StreakState(), DAY1)
    state = update_streak(state, DAY1 + timedelta(days=1))
    state = update_streak(state, DAY1 + timedelta(days=2))
    assert state.current_streak == 3

    state = update_streak(state, DAY1 + timedelta(days=5))  # skipped days 3 and 4
    assert state.current_streak == 1
    assert state.last_practice_date == DAY1 + timedelta(days=5)


def test_practicing_earlier_the_same_day_repeatedly_stays_at_one() -> None:
    state = StreakState()
    for _ in range(5):
        state = update_streak(state, DAY1)
    assert state.current_streak == 1
