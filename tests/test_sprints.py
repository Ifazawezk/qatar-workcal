import datetime as dt

import pytest

from qatar_workcal.sprints import Member, Plan, parse_leave, plan_from_dict, plan_sprints
from qatar_workcal.workcal import WorkCalendar

D = dt.date
CAL = WorkCalendar()


def test_two_week_sprints_in_january():
    sprints = plan_sprints(CAL, Plan(D(2026, 1, 4), length=10, count=2, members=[Member("A")]))
    assert (sprints[0].start, sprints[0].end) == (D(2026, 1, 4), D(2026, 1, 15))
    assert (sprints[1].start, sprints[1].end) == (D(2026, 1, 18), D(2026, 1, 29))
    assert sprints[0].capacity == 80


def test_start_on_a_weekend_moves_to_sunday():
    sprints = plan_sprints(CAL, Plan(D(2026, 1, 2), count=1))
    assert sprints[0].start == D(2026, 1, 4)


def test_ramadan_lowers_capacity():
    sprint = plan_sprints(CAL, Plan(D(2026, 2, 15), count=1, members=[Member("A")]))[0]
    assert sprint.ramadan_days == 7
    assert sprint.capacity == 3 * 8 + 7 * 6


def test_holidays_stretch_the_sprint():
    sprint = plan_sprints(CAL, Plan(D(2026, 3, 15), count=1, members=[Member("A")]))[0]
    assert [h.name for h in sprint.holidays] == ["Eid al-Fitr"] * 3
    assert sprint.end == D(2026, 3, 31)
    assert len(sprint.days) == 10


def test_leave_allocation_and_focus():
    members = [
        Member("A", leave=[(D(2026, 1, 4), D(2026, 1, 8))]),
        Member("B", allocation=0.5),
    ]
    sprint = plan_sprints(CAL, Plan(D(2026, 1, 4), count=1, focus=0.8, members=members))[0]
    assert sprint.by_member == {"A": 32.0, "B": 32.0}
    assert sprint.capacity == 64


def test_leave_on_a_holiday_is_not_counted_twice():
    members = [Member("A", leave=[(D(2026, 3, 20), D(2026, 3, 24))])]
    sprint = plan_sprints(CAL, Plan(D(2026, 3, 15), count=1, members=members))[0]
    # Five Ramadan days (15 to 19 March) and five normal days after Eid.
    assert sprint.capacity == 5 * 6 + 5 * 8


def test_parse_leave():
    assert parse_leave("2026-03-15..2026-03-26") == (D(2026, 3, 15), D(2026, 3, 26))
    assert parse_leave("2026-03-15") == (D(2026, 3, 15), D(2026, 3, 15))
    assert parse_leave({"from": "2026-01-01", "to": "2026-01-02"}) == (D(2026, 1, 1), D(2026, 1, 2))
    with pytest.raises(ValueError):
        parse_leave("2026-03-26..2026-03-15")


def test_plan_from_dict():
    plan = plan_from_dict({"start": "2026-01-04", "length": 5, "members": ["Noor", {"name": "Sami", "allocation": 0.5}]})
    assert [m.name for m in plan.members] == ["Noor", "Sami"]
    with pytest.raises(ValueError):
        plan_from_dict({"length": 5})
    with pytest.raises(ValueError):
        plan_from_dict({"start": "2026-01-04", "members": [{"name": "X", "allocation": 2}]})
    with pytest.raises(ValueError):
        plan_from_dict({"start": "2026-01-04", "length": 0})


def test_release_avoids_thursday():
    sprint = plan_sprints(CAL, Plan(D(2026, 1, 4), count=1))[0]
    assert sprint.end == D(2026, 1, 15)  # Thursday
    assert sprint.release == D(2026, 1, 14)
    assert sprint.release_note == "moved from Thu 15 Jan: no releases on Thursday"


def test_release_avoids_the_eve_of_eid():
    # Sprint ends Tue 26 May; Eid al-Adha starts Wed 27 May.
    sprint = plan_sprints(CAL, Plan(D(2026, 5, 13), count=1))[0]
    assert sprint.end == D(2026, 5, 26)
    assert sprint.release == D(2026, 5, 25)
    assert "Eid al-Adha on Wed 27 May" in sprint.release_note


def test_longer_freeze():
    sprint = plan_sprints(CAL, Plan(D(2026, 5, 13), count=1, freeze_days=3))[0]
    assert sprint.release == D(2026, 5, 20)  # Thursday 21 May is skipped too


def test_no_safe_day():
    from qatar_workcal.sprints import release_day
    assert release_day(CAL, [D(2026, 1, 8)])[0] is None


def test_release_days_from_dict():
    plan = plan_from_dict({"start": "2026-01-04", "release_days": ["sun", "thu"], "freeze_days": 0})
    sprint = plan_sprints(CAL, plan)[0]
    assert sprint.release == D(2026, 1, 15) and sprint.release_note == ""
