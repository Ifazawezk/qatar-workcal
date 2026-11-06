"""Sprint planning on the working calendar: dates, capacity and leave."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .holidays import Holiday
from .workcal import WorkCalendar, parse_date


@dataclass
class Member:
    name: str
    allocation: float = 1.0
    leave: list[tuple[dt.date, dt.date]] = field(default_factory=list)

    def on_leave(self, day: dt.date) -> bool:
        return any(a <= day <= b for a, b in self.leave)


@dataclass
class Plan:
    start: dt.date
    length: int = 10
    count: int = 6
    focus: float = 1.0
    members: list[Member] = field(default_factory=list)


@dataclass
class Sprint:
    number: int
    days: list[dt.date]
    capacity: float
    by_member: dict[str, float]
    ramadan_days: int
    holidays: list[Holiday]

    @property
    def start(self) -> dt.date:
        return self.days[0]

    @property
    def end(self) -> dt.date:
        return self.days[-1]


def parse_leave(item: Any) -> tuple[dt.date, dt.date]:
    """"2026-03-15..2026-03-26", a single date, or {"from": ..., "to": ...}."""
    if isinstance(item, dict):
        return parse_date(item["from"]), parse_date(item["to"])
    text = str(item)
    if ".." in text:
        a, b = text.split("..", 1)
        first, last = parse_date(a), parse_date(b)
    else:
        first = last = parse_date(text)
    if last < first:
        raise ValueError(f"leave {text!r} ends before it starts")
    return first, last


def plan_from_dict(data: dict[str, Any]) -> Plan:
    if "start" not in data:
        raise ValueError("the plan needs a start date")
    members = []
    for m in data.get("members") or []:
        if isinstance(m, str):
            m = {"name": m}
        allocation = float(m.get("allocation", 1.0))
        if not 0 < allocation <= 1:
            raise ValueError(f"{m['name']}: allocation must be between 0 and 1")
        members.append(Member(str(m["name"]), allocation, [parse_leave(x) for x in m.get("leave") or []]))
    plan = Plan(
        start=parse_date(data["start"]),
        length=int(data.get("length", 10)),
        count=int(data.get("count", 6)),
        focus=float(data.get("focus", 1.0)),
        members=members,
    )
    if plan.length < 1 or plan.count < 1:
        raise ValueError("length and count must be at least 1")
    return plan


def load_plan(path: str | Path) -> tuple[Plan, dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return plan_from_dict(data), data


def capacity(cal: WorkCalendar, days: list[dt.date], members: list[Member], focus: float = 1.0) -> dict[str, float]:
    """Hours per member: calendar hours on days they are not on leave, scaled."""
    return {
        m.name: round(sum(cal.hours_on(d) for d in days if not m.on_leave(d)) * m.allocation * focus, 1)
        for m in members
    }


def plan_sprints(cal: WorkCalendar, plan: Plan) -> list[Sprint]:
    sprints = []
    day = cal.next_working_day(plan.start)
    for number in range(1, plan.count + 1):
        days = [day]
        while len(days) < plan.length:
            days.append(cal.next_working_day(days[-1], include=False))
        by_member = capacity(cal, days, plan.members, plan.focus)
        holidays = [
            h for y in range(days[0].year, days[-1].year + 1)
            for h in cal.holidays(y) if days[0] <= h.date <= days[-1]
        ]
        sprints.append(Sprint(
            number=number,
            days=days,
            capacity=round(sum(by_member.values()), 1),
            by_member=by_member,
            ramadan_days=sum(cal.is_ramadan(d) for d in days),
            holidays=holidays,
        ))
        day = cal.next_working_day(days[-1], include=False)
    return sprints
