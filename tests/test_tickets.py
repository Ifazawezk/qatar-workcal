import datetime as dt

import pytest

from qatar_workcal.tickets import (
    DEFAULT_POLICIES,
    Ticket,
    evaluate,
    load_tickets,
    parse_pauses,
    policies_from_config,
)
from qatar_workcal.workcal import WorkCalendar

T = dt.datetime
CAL = WorkCalendar()
NOW = T(2026, 3, 25, 12)


def test_policies_from_config():
    pol = policies_from_config({"P1": {"hours": "2h", "tier": "24x7"}, "P2": 6})
    assert pol["P1"].minutes == 120 and pol["P1"].tier == "24x7"
    assert pol["P2"].minutes == 360 and pol["P2"].tier == "business"
    assert policies_from_config(None) == DEFAULT_POLICIES
    with pytest.raises(ValueError):
        policies_from_config({"P1": {"hours": 1, "tier": "always"}})


def test_parse_pauses():
    assert parse_pauses("2026-01-04 10:00/2026-01-04 11:00; 2026-01-05 09:00/") == (
        (T(2026, 1, 4, 10), T(2026, 1, 4, 11)),
        (T(2026, 1, 5, 9), None),
    )
    assert parse_pauses("") == ()


def test_states():
    pol = DEFAULT_POLICIES
    met = evaluate(Ticket("1", "P2", T(2026, 3, 19, 15), resolved=T(2026, 3, 25, 10)), CAL, pol, NOW)
    assert met.state == "met" and met.due == T(2026, 3, 25, 16) and met.used == 180
    late = evaluate(Ticket("2", "P1", T(2026, 3, 19, 15), resolved=T(2026, 3, 20, 9)), CAL, pol, NOW)
    assert late.state == "breached" and late.due == T(2026, 3, 19, 19)
    risk = evaluate(Ticket("3", "P2", T(2026, 3, 19, 15)), CAL, pol, T(2026, 3, 25, 14))
    assert risk.state == "at risk" and risk.remaining == 120
    still = evaluate(Ticket("4", "P2", T(2026, 3, 25, 9)), CAL, pol, NOW)
    assert still.state == "open"
    over = evaluate(Ticket("5", "P2", T(2026, 3, 1, 9)), CAL, pol, NOW)
    assert over.state == "breached"
    paused = evaluate(Ticket("6", "P3", T(2026, 3, 24, 9), pauses=((T(2026, 3, 25, 10), None),)), CAL, pol, NOW)
    assert paused.state == "paused" and paused.due is None and paused.used == 120


def test_unknown_priority():
    with pytest.raises(ValueError):
        evaluate(Ticket("1", "P9", T(2026, 1, 4, 9)), CAL, DEFAULT_POLICIES, NOW)


def test_load_tickets(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text(
        "id,priority,opened,resolved,paused,title\n"
        "QD-1,P2,2026-03-19 15:00,2026-03-25 10:00,,VPN down\n"
        "QD-2,P3,2026-03-24T09:00+03:00,,2026-03-25 10:00/,Waiting on customer\n",
        encoding="utf-8",
    )
    tickets = load_tickets(path)
    assert [t.id for t in tickets] == ["QD-1", "QD-2"]
    assert tickets[0].resolved == T(2026, 3, 25, 10)
    assert tickets[1].pauses == ((T(2026, 3, 25, 10), None),)


def test_load_tickets_errors(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text("id,opened\n1,2026-01-01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns priority"):
        load_tickets(path)
    path.write_text("id,priority,opened\n1,P1,yesterday\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_tickets(path)
