import datetime as dt

import pytest

from qatar_workcal.sla import due, elapsed, format_minutes, parse_duration
from qatar_workcal.workcal import Config, WorkCalendar

T = dt.datetime
CAL = WorkCalendar()


def test_same_day_and_overnight():
    assert due(T(2026, 1, 4, 9), 240, CAL) == T(2026, 1, 4, 14)  # skips lunch
    assert due(T(2026, 1, 4, 9), 480, CAL) == T(2026, 1, 5, 9)


def test_due_exactly_at_close_stays_on_the_same_day():
    assert due(T(2026, 1, 4, 8), 480, CAL) == T(2026, 1, 4, 17)


def test_thursday_afternoon_runs_over_the_weekend():
    assert due(T(2026, 1, 8, 16), 240, CAL) == T(2026, 1, 11, 11)


def test_opened_on_friday_starts_on_sunday():
    assert due(T(2026, 1, 9, 10), 120, CAL) == T(2026, 1, 11, 10)


def test_opened_in_the_evening_starts_next_morning():
    assert due(T(2026, 1, 5, 21, 30), 60, CAL) == T(2026, 1, 6, 9)


def test_ramadan_day_is_six_hours():
    # Sunday 1 March 2026: 09-12 and 13-16, then 2 more hours on Monday.
    assert due(T(2026, 3, 1, 9), 480, CAL) == T(2026, 3, 2, 11)


def test_last_hour_before_eid_al_fitr():
    # Thursday 19 March is the last day of Ramadan. Eid al-Fitr (Friday 20 March)
    # plus the weekend and three working days of leave closes the desk until Wednesday.
    assert due(T(2026, 3, 19, 15), 480, CAL) == T(2026, 3, 25, 16)


def test_ticket_opened_during_eid_waits_for_the_first_working_day():
    assert due(T(2026, 3, 23, 10), 60, CAL) == T(2026, 3, 25, 9)


def test_before_eid_al_adha():
    # 0.5h on Tuesday, then Eid from Wednesday 27 May to Sunday 31 May.
    assert due(T(2026, 5, 26, 16, 30), 240, CAL) == T(2026, 6, 1, 11, 30)


def test_first_day_of_ramadan_uses_ramadan_hours():
    assert due(T(2026, 2, 17, 16), 240, CAL) == T(2026, 2, 18, 12)


def test_announced_eid_date_moves_the_due_time():
    opened = T(2026, 5, 25, 16, 30)
    assert due(opened, 240, CAL) == T(2026, 5, 26, 11, 30)
    # If Eid al-Adha is announced for Tuesday 26 May, the leave runs Tue to Thu.
    cal = WorkCalendar(Config.from_dict({"overrides": {"eid_al_adha": "2026-05-26"}}))
    assert due(opened, 240, cal) == T(2026, 5, 31, 11, 30)


def test_24x7_ignores_holidays_and_weekends():
    assert due(T(2026, 3, 19, 15), 480, CAL, tier="24x7") == T(2026, 3, 19, 23)
    assert due(T(2026, 1, 9, 22), 240, CAL, tier="24x7") == T(2026, 1, 10, 2)


def test_pause_stops_the_clock():
    pauses = [(T(2026, 1, 4, 10), T(2026, 1, 4, 14))]
    assert due(T(2026, 1, 4, 9), 480, CAL, pauses=pauses) == T(2026, 1, 5, 12)


def test_pause_outside_office_hours_changes_nothing():
    pauses = [(T(2026, 1, 8, 18), T(2026, 1, 11, 7))]
    assert due(T(2026, 1, 8, 16), 240, CAL, pauses=pauses) == T(2026, 1, 11, 11)


def test_pause_that_spans_eid():
    pauses = [(T(2026, 3, 19, 15, 30), T(2026, 3, 25, 10))]
    assert due(T(2026, 3, 19, 15), 120, CAL, pauses=pauses) == T(2026, 3, 25, 11, 30)


def test_open_pause_means_no_due_time():
    assert due(T(2026, 1, 4, 9), 480, CAL, pauses=[(T(2026, 1, 4, 10), None)]) is None


def test_overlapping_pauses_are_merged():
    pauses = [(T(2026, 1, 4, 1), T(2026, 1, 4, 3)), (T(2026, 1, 4, 2), T(2026, 1, 4, 4)), (T(2026, 1, 4, 3, 30), None)]
    assert due(T(2026, 1, 4, 0), 240, CAL, tier="24x7", pauses=pauses) is None
    pauses = [(T(2026, 1, 4, 1), T(2026, 1, 4, 3)), (T(2026, 1, 4, 2), T(2026, 1, 4, 4))]
    assert due(T(2026, 1, 4, 0), 240, CAL, tier="24x7", pauses=pauses) == T(2026, 1, 4, 7)


def test_bad_pause_and_tier():
    with pytest.raises(ValueError):
        due(T(2026, 1, 4, 9), 60, CAL, pauses=[(T(2026, 1, 4, 10), T(2026, 1, 4, 9))])
    with pytest.raises(ValueError):
        due(T(2026, 1, 4, 9), 60, CAL, tier="gold")


def test_zero_minutes_is_the_next_running_moment():
    assert due(T(2026, 1, 9, 10), 0, CAL) == T(2026, 1, 11, 8)


def test_elapsed_counts_only_business_time():
    assert elapsed(T(2026, 3, 19, 15), T(2026, 3, 25, 10), CAL) == 180
    assert elapsed(T(2026, 3, 19, 15), T(2026, 3, 19, 14), CAL) == 0
    assert elapsed(T(2026, 1, 4, 9), T(2026, 1, 4, 16), CAL, pauses=[(T(2026, 1, 4, 10), None)]) == 60
    assert elapsed(T(2026, 1, 9, 22), T(2026, 1, 10, 2), CAL, tier="24x7") == 240


def test_due_and_elapsed_agree():
    opened = T(2026, 2, 26, 11, 17)
    for minutes in (1, 59, 360, 1000, 3000):
        end = due(opened, minutes, CAL)
        assert elapsed(opened, end, CAL) == minutes


@pytest.mark.parametrize("text,minutes", [("8h", 480), ("90m", 90), ("1h30m", 90), ("2.5h", 150), ("4", 240), (3, 180)])
def test_parse_duration(text, minutes):
    assert parse_duration(text) == minutes


@pytest.mark.parametrize("text", ["", "abc", "8d", "h"])
def test_parse_duration_rejects(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_format_minutes():
    assert format_minutes(90) == "1h30m"
    assert format_minutes(-30) == "-0h30m"
