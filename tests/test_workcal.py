import datetime as dt

import pytest

from qatar_workcal.workcal import Config, WorkCalendar, parse_datetime, parse_span

D = dt.date


@pytest.fixture
def cal():
    return WorkCalendar()


def test_friday_and_saturday_are_off(cal):
    assert not cal.is_working_day(D(2026, 1, 2))  # Friday
    assert not cal.is_working_day(D(2026, 1, 3))  # Saturday
    assert cal.is_working_day(D(2026, 1, 4))  # Sunday


def test_normal_and_ramadan_hours(cal):
    assert cal.hours_on(D(2026, 1, 5)) == 8
    assert cal.is_ramadan(D(2026, 2, 18))
    assert cal.hours_on(D(2026, 2, 18)) == 6
    assert cal.is_ramadan(D(2026, 3, 19))
    assert not cal.is_ramadan(D(2026, 3, 20))


def test_eid_is_off(cal):
    assert cal.describe(D(2026, 3, 22)) == "Eid al-Fitr"
    assert cal.hours_on(D(2026, 3, 22)) == 0
    assert cal.next_working_day(D(2026, 3, 20)) == D(2026, 3, 25)


def test_add_working_days_crosses_eid(cal):
    assert cal.add_working_days(D(2026, 3, 19), 1) == D(2026, 3, 25)
    assert cal.add_working_days(D(2026, 3, 20), 0) == D(2026, 3, 25)


def test_working_days_in_a_range(cal):
    days = cal.working_days(D(2026, 5, 24), D(2026, 6, 4))
    assert D(2026, 5, 27) not in days and D(2026, 5, 31) not in days
    assert len(days) == 7


def test_config_from_dict():
    cfg = Config.from_dict({
        "weekend": ["Friday"],
        "hours": ["07:30-12:30", "13:30-16:30"],
        "holidays": [{"date": "2026-04-01", "name": "Founders day"}, "2026-04-02"],
        "remove": ["2026-02-10"],
        "overrides": {"eid_al_fitr": "2026-03-21"},
        "sport_day": True,
    })
    cal = WorkCalendar(cfg)
    assert cal.is_working_day(D(2026, 1, 3))  # Saturday now works
    assert cal.hours_on(D(2026, 1, 3)) == 8
    assert cal.holiday(D(2026, 4, 1)).name == "Founders day"
    assert cal.holiday(D(2026, 4, 2)).kind == "company"
    assert cal.holiday(D(2026, 2, 10)) is None
    assert cal.is_ramadan(D(2026, 3, 20))


def test_bad_config():
    with pytest.raises(ValueError):
        Config.from_dict({"weekends": ["fri"]})
    with pytest.raises(ValueError):
        Config.from_dict({"overrides": {"christmas": "2026-12-25"}})
    with pytest.raises(ValueError):
        parse_span("17:00-08:00")


def test_parse_datetime_converts_offsets():
    assert parse_datetime("2026-03-01T06:00:00Z") == dt.datetime(2026, 3, 1, 9, 0)
    assert parse_datetime("2026-03-01 09:15") == dt.datetime(2026, 3, 1, 9, 15)


def test_no_working_days_at_all():
    cal = WorkCalendar(Config.from_dict({"weekend": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}))
    with pytest.raises(ValueError):
        cal.next_working_day(D(2026, 1, 1))
