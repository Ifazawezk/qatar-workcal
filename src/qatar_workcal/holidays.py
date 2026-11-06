"""Public holidays in Qatar and the dates of Ramadan.

Hijri dates come from the Umm al-Qura calendar through the hijridate package.
Qatar announces the start of Ramadan and both Eids after the crescent is sighted,
so the real first day can differ from the calculated one by a day. Pass the
announced date as an override when it is out.

Leave days follow Article 78 of the Labour Law (Law No. 14 of 2004): three working
days for each Eid and one day for the national day. The three days that Article 78
leaves to the employer go in the config as company holidays.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from hijridate import Gregorian, Hijri

ONE_DAY = dt.timedelta(days=1)

# Hijri month and day each event starts on.
HIJRI_START = {
    "ramadan": (9, 1),
    "eid_al_fitr": (10, 1),
    "eid_al_adha": (12, 10),
}
NAMES = {
    "eid_al_fitr": "Eid al-Fitr",
    "eid_al_adha": "Eid al-Adha",
    "national_day": "National Day",
    "sport_day": "National Sport Day",
}
# How far an override may sit from the calculated date and still replace it.
OVERRIDE_WINDOW = 5


@dataclass(frozen=True)
class Holiday:
    date: dt.date
    name: str
    kind: str


def hijri_to_date(year: int, month: int, day: int) -> dt.date:
    g = Hijri(year, month, day).to_gregorian()
    return dt.date(g.year, g.month, g.day)


def to_hijri(day: dt.date) -> tuple[int, int, int]:
    h = Gregorian(day.year, day.month, day.day).to_hijri()
    return h.year, h.month, h.day


def calculated_starts(kind: str, year: int) -> list[dt.date]:
    """Umm al-Qura start dates of an event that fall in a Gregorian year."""
    month, day = HIJRI_START[kind]
    try:
        first = to_hijri(dt.date(year, 1, 1))[0]
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{year} is outside the range hijridate supports (1924 to 2077)") from exc
    out = []
    for hijri_year in range(first, first + 3):
        try:
            start = hijri_to_date(hijri_year, month, day)
        except (OverflowError, ValueError):
            continue
        if start.year == year:
            out.append(start)
    return out


def event_starts(kind: str, year: int, overrides: Iterable[dt.date] = ()) -> list[dt.date]:
    """Start dates for a year, with announced dates swapped in for calculated ones."""
    overrides = list(overrides)
    out = []
    for start in calculated_starts(kind, year):
        near = [o for o in overrides if abs((o - start).days) <= OVERRIDE_WINDOW]
        out.append(min(near, key=lambda o: abs((o - start).days)) if near else start)
    return out


def check_overrides(kind: str, overrides: Iterable[dt.date]) -> None:
    """Raise if an override is not near any calculated start, which is usually a typo."""
    for o in overrides:
        starts = calculated_starts(kind, o.year) + calculated_starts(kind, o.year - 1) + calculated_starts(kind, o.year + 1)
        if not any(abs((o - s).days) <= OVERRIDE_WINDOW for s in starts):
            raise ValueError(f"{kind} override {o} is not within {OVERRIDE_WINDOW} days of a calculated date")


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def eid_days(start: dt.date, count: int, weekend: Iterable[int]) -> list[dt.date]:
    """`count` working days from `start`; weekend days in between are already off."""
    weekend = set(weekend)
    days, day = [], start
    while len(days) < count:
        if day.weekday() not in weekend:
            days.append(day)
        day += ONE_DAY
    return days


def public_holidays(
    year: int,
    weekend: Iterable[int] = (4, 5),
    eid_length: int = 3,
    sport_day: bool = True,
    overrides: dict[str, Iterable[dt.date]] | None = None,
) -> list[Holiday]:
    weekend = tuple(weekend)
    overrides = overrides or {}
    found: dict[dt.date, Holiday] = {}
    for kind in ("eid_al_fitr", "eid_al_adha"):
        # An Eid that starts in late December can run into January.
        for y in (year - 1, year):
            for start in event_starts(kind, y, overrides.get(kind, ())):
                for day in eid_days(start, eid_length, weekend):
                    if day.year == year:
                        found.setdefault(day, Holiday(day, NAMES[kind], kind))
    national = dt.date(year, 12, 18)
    found.setdefault(national, Holiday(national, NAMES["national_day"], "national_day"))
    if sport_day:
        sport = nth_weekday(year, 2, 1, 2)
        found.setdefault(sport, Holiday(sport, NAMES["sport_day"], "sport_day"))
    return sorted(found.values(), key=lambda h: h.date)


def ramadan_ranges(year: int, overrides: dict[str, Iterable[dt.date]] | None = None) -> list[tuple[dt.date, dt.date]]:
    """First and last day of each Ramadan that starts in `year`.

    Ramadan ends the day before Eid al-Fitr, so an Eid override also moves the end.
    """
    overrides = overrides or {}
    fitr = []
    for y in (year, year + 1):
        fitr += event_starts("eid_al_fitr", y, overrides.get("eid_al_fitr", ()))
    out = []
    for start in event_starts("ramadan", year, overrides.get("ramadan", ())):
        eid = min(d for d in fitr if d > start)
        out.append((start, eid - ONE_DAY))
    return out
