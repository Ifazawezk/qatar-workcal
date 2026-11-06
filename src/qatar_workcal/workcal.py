"""The working calendar: weekend, office hours, Ramadan hours and holidays."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .holidays import ONE_DAY, Holiday, check_overrides, public_holidays, ramadan_ranges

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
QATAR = dt.timezone(dt.timedelta(hours=3))

Span = tuple[dt.time, dt.time]


def parse_span(text: str) -> Span:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*", text)
    if not m:
        raise ValueError(f"bad hours {text!r}, expected HH:MM-HH:MM")
    h1, m1, h2, m2 = map(int, m.groups())
    start, end = dt.time(h1, m1), dt.time(h2, m2)
    if end <= start:
        raise ValueError(f"hours {text!r} end before they start")
    return start, end


def parse_weekday(text: str | int) -> int:
    if isinstance(text, int):
        return text
    key = str(text).strip().lower()[:3]
    if key not in WEEKDAYS:
        raise ValueError(f"unknown weekday {text!r}")
    return WEEKDAYS[key]


def parse_date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value).strip())


def parse_datetime(value: Any) -> dt.datetime:
    """Read a date and time as Qatar local time. Times with an offset are converted."""
    if isinstance(value, dt.datetime):
        moment = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        moment = dt.datetime.fromisoformat(text)
    if moment.tzinfo is not None:
        moment = moment.astimezone(QATAR).replace(tzinfo=None)
    return moment


def span_hours(spans: tuple[Span, ...]) -> float:
    total = 0
    for start, end in spans:
        total += (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    return total / 60


@dataclass
class Config:
    weekend: tuple[int, ...] = (4, 5)
    hours: tuple[Span, ...] = (parse_span("08:00-12:00"), parse_span("13:00-17:00"))
    ramadan_hours: tuple[Span, ...] = (parse_span("09:00-12:00"), parse_span("13:00-16:00"))
    sport_day: bool = True
    eid_length: int = 3
    company_holidays: dict[dt.date, str] = field(default_factory=dict)
    remove: frozenset[dt.date] = frozenset()
    overrides: dict[str, tuple[dt.date, ...]] = field(default_factory=dict)
    sla: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Config":
        data = dict(data or {})
        known = {"weekend", "hours", "ramadan_hours", "sport_day", "eid_length", "holidays", "remove", "overrides", "sla"}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown config keys: {', '.join(sorted(unknown))}")
        cfg = cls()
        if "weekend" in data:
            cfg.weekend = tuple(sorted(parse_weekday(d) for d in data["weekend"] or []))
        if "hours" in data:
            cfg.hours = tuple(parse_span(s) for s in data["hours"])
        if "ramadan_hours" in data:
            cfg.ramadan_hours = tuple(parse_span(s) for s in data["ramadan_hours"])
        cfg.sport_day = bool(data.get("sport_day", True))
        cfg.eid_length = int(data.get("eid_length", 3))
        for item in data.get("holidays") or []:
            if isinstance(item, dict):
                cfg.company_holidays[parse_date(item["date"])] = str(item.get("name", "Company holiday"))
            else:
                cfg.company_holidays[parse_date(item)] = "Company holiday"
        cfg.remove = frozenset(parse_date(d) for d in data.get("remove") or [])
        for kind, dates in (data.get("overrides") or {}).items():
            if kind not in ("ramadan", "eid_al_fitr", "eid_al_adha"):
                raise ValueError(f"overrides can set ramadan, eid_al_fitr or eid_al_adha, not {kind!r}")
            parsed = tuple(parse_date(d) for d in (dates if isinstance(dates, list) else [dates]))
            check_overrides(kind, parsed)
            cfg.overrides[kind] = parsed
        cfg.sla = dict(data.get("sla") or {})
        return cfg

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))


class WorkCalendar:
    """Answers "is this a working day" and "which hours are worked" for a date."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._holidays: dict[int, dict[dt.date, Holiday]] = {}
        self._ramadan: dict[int, list[tuple[dt.date, dt.date]]] = {}

    def holidays(self, year: int) -> list[Holiday]:
        if year not in self._holidays:
            cfg = self.config
            found = {
                h.date: h
                for h in public_holidays(year, cfg.weekend, cfg.eid_length, cfg.sport_day, cfg.overrides)
            }
            for day, name in cfg.company_holidays.items():
                if day.year == year:
                    found.setdefault(day, Holiday(day, name, "company"))
            for day in cfg.remove:
                found.pop(day, None)
            self._holidays[year] = dict(sorted(found.items()))
        return list(self._holidays[year].values())

    def holiday(self, day: dt.date) -> Holiday | None:
        self.holidays(day.year)
        return self._holidays[day.year].get(day)

    def ramadan(self, year: int) -> list[tuple[dt.date, dt.date]]:
        if year not in self._ramadan:
            self._ramadan[year] = ramadan_ranges(year, self.config.overrides)
        return self._ramadan[year]

    def is_ramadan(self, day: dt.date) -> bool:
        return any(start <= day <= end for y in (day.year - 1, day.year) for start, end in self.ramadan(y))

    def is_weekend(self, day: dt.date) -> bool:
        return day.weekday() in self.config.weekend

    def is_working_day(self, day: dt.date) -> bool:
        return not self.is_weekend(day) and self.holiday(day) is None

    def spans(self, day: dt.date) -> tuple[Span, ...]:
        if not self.is_working_day(day):
            return ()
        return self.config.ramadan_hours if self.is_ramadan(day) else self.config.hours

    def intervals(self, day: dt.date) -> list[tuple[dt.datetime, dt.datetime]]:
        out = []
        for start, end in self.spans(day):
            out.append((dt.datetime.combine(day, start), dt.datetime.combine(day, end)))
        return out

    def hours_on(self, day: dt.date) -> float:
        return sum((e - s).total_seconds() for s, e in self.intervals(day)) / 3600

    def next_working_day(self, day: dt.date, include: bool = True) -> dt.date:
        if not include:
            day += ONE_DAY
        for _ in range(3660):
            if self.is_working_day(day):
                return day
            day += ONE_DAY
        raise ValueError("no working day within ten years; check the weekend setting")

    def add_working_days(self, day: dt.date, n: int) -> dt.date:
        """The nth working day after `day` (n=0 gives `day` if it is a working day)."""
        day = self.next_working_day(day)
        for _ in range(n):
            day = self.next_working_day(day, include=False)
        return day

    def working_days(self, start: dt.date, end: dt.date) -> list[dt.date]:
        days, day = [], start
        while day <= end:
            if self.is_working_day(day):
                days.append(day)
            day += ONE_DAY
        return days

    def describe(self, day: dt.date) -> str:
        holiday = self.holiday(day)
        if holiday:
            return holiday.name
        if self.is_weekend(day):
            return "weekend"
        return "Ramadan hours" if self.is_ramadan(day) else "working day"
