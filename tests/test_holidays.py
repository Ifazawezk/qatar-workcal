import datetime as dt

import pytest

from qatar_workcal.holidays import (
    calculated_starts,
    check_overrides,
    eid_days,
    event_starts,
    nth_weekday,
    public_holidays,
    ramadan_ranges,
    to_hijri,
)

D = dt.date


def test_umm_al_qura_dates_for_2026():
    assert calculated_starts("ramadan", 2026) == [D(2026, 2, 18)]
    assert calculated_starts("eid_al_fitr", 2026) == [D(2026, 3, 20)]
    assert calculated_starts("eid_al_adha", 2026) == [D(2026, 5, 27)]


def test_hijri_round_trip():
    assert to_hijri(D(2026, 3, 20)) == (1447, 10, 1)


def test_eid_days_skip_the_weekend():
    # 2026-03-20 is a Friday, so the three working days are Sun to Tue.
    assert eid_days(D(2026, 3, 20), 3, (4, 5)) == [D(2026, 3, 22), D(2026, 3, 23), D(2026, 3, 24)]
    assert eid_days(D(2026, 3, 20), 3, (6,)) == [D(2026, 3, 20), D(2026, 3, 21), D(2026, 3, 23)]


def test_public_holidays_2026():
    days = {h.date: h.kind for h in public_holidays(2026)}
    assert days[D(2026, 12, 18)] == "national_day"
    assert days[D(2026, 2, 10)] == "sport_day"
    assert [d for d, k in days.items() if k == "eid_al_adha"] == [D(2026, 5, 27), D(2026, 5, 28), D(2026, 5, 31)]
    assert len(days) == 8


def test_sport_day_can_be_turned_off():
    assert all(h.kind != "sport_day" for h in public_holidays(2026, sport_day=False))


def test_second_tuesday():
    assert nth_weekday(2027, 2, 1, 2) == D(2027, 2, 9)


def test_override_moves_eid_and_ramadan_end():
    over = {"eid_al_fitr": [D(2026, 3, 21)]}
    assert event_starts("eid_al_fitr", 2026, over["eid_al_fitr"]) == [D(2026, 3, 21)]
    assert ramadan_ranges(2026, over) == [(D(2026, 2, 18), D(2026, 3, 20))]
    fitr = [h.date for h in public_holidays(2026, overrides=over) if h.kind == "eid_al_fitr"]
    assert fitr[0] == D(2026, 3, 22)


def test_far_override_is_rejected():
    with pytest.raises(ValueError):
        check_overrides("eid_al_adha", [D(2026, 7, 1)])
    check_overrides("eid_al_adha", [D(2026, 5, 26)])


def test_ramadan_2027():
    assert ramadan_ranges(2027) == [(D(2027, 2, 8), D(2027, 3, 8))]


def test_out_of_range_year():
    with pytest.raises(ValueError):
        calculated_starts("ramadan", 2090)
