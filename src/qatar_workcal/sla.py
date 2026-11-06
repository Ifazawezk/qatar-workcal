"""SLA clock: when is a ticket due, counting only the time the clock runs.

The business tier counts office hours on the working calendar, so evenings, the
weekend, public holidays and the short Ramadan day all slow the clock down. The
24x7 tier counts every minute. Both stop while a ticket is paused, for example
while the team waits on the customer.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Iterable, Iterator, Optional

from .workcal import WorkCalendar

TIERS = ("business", "24x7")
MAX_DAYS = 3660

Pause = tuple[dt.datetime, Optional[dt.datetime]]


def parse_duration(text: str | int | float) -> int:
    """Minutes in "8h", "90m", "1h30m", "2.5h" or a bare number of hours."""
    if isinstance(text, (int, float)):
        return round(text * 60)
    s = str(text).strip().lower().replace(" ", "")
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return round(float(s) * 60)
    m = re.fullmatch(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+)m(?:in)?)?", s)
    if not s or not m or not any(m.groups()):
        raise ValueError(f"bad duration {text!r}, use something like 8h, 90m or 1h30m")
    return round(float(m.group(1) or 0) * 60) + int(m.group(2) or 0)


def format_minutes(minutes: float) -> str:
    sign = "-" if minutes < 0 else ""
    h, m = divmod(round(abs(minutes)), 60)
    return f"{sign}{h}h{m:02d}m"


def _clock_intervals(start: dt.datetime, cal: WorkCalendar, tier: str) -> Iterator[tuple[dt.datetime, dt.datetime]]:
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {', '.join(TIERS)}, not {tier!r}")
    if tier == "24x7":
        yield start, dt.datetime.max
        return
    day = start.date()
    for _ in range(MAX_DAYS):
        for s, e in cal.intervals(day):
            s = max(s, start)
            if s < e:
                yield s, e
        day += dt.timedelta(days=1)
    raise ValueError("the clock found no working time in ten years; check the calendar")


def _merge(pauses: Iterable[Pause]) -> list[Pause]:
    out: list[list] = []
    for start, end in sorted(pauses, key=lambda p: p[0]):
        if end is not None and end < start:
            raise ValueError(f"pause ends before it starts: {start} to {end}")
        if out and (out[-1][1] is None or start <= out[-1][1]):
            if out[-1][1] is not None:
                out[-1][1] = None if end is None else max(out[-1][1], end)
            continue
        out.append([start, end])
    return [(s, e) for s, e in out]


def _running(start: dt.datetime, cal: WorkCalendar, tier: str, pauses: Iterable[Pause]) -> Iterator[tuple[dt.datetime, dt.datetime]]:
    """Intervals where the clock runs, with paused time cut out.

    Stops for good at a pause that has no end yet.
    """
    pauses = _merge(pauses)
    for s, e in _clock_intervals(start, cal, tier):
        for ps, pe in pauses:
            if pe is not None and pe <= s:
                continue
            if ps >= e:
                break
            if ps > s:
                yield s, ps
            if pe is None:
                return
            s = max(s, pe)
            if s >= e:
                break
        if s < e:
            yield s, e


def due(
    opened: dt.datetime,
    minutes: int,
    cal: WorkCalendar,
    tier: str = "business",
    pauses: Iterable[Pause] = (),
) -> dt.datetime | None:
    """When the SLA runs out, or None while the ticket sits in an open pause."""
    left = dt.timedelta(minutes=minutes)
    for s, e in _running(opened, cal, tier, pauses):
        if left <= dt.timedelta(0):
            return s
        if e - s >= left:
            return s + left
        left -= e - s
    return None


def elapsed(
    opened: dt.datetime,
    until: dt.datetime,
    cal: WorkCalendar,
    tier: str = "business",
    pauses: Iterable[Pause] = (),
) -> float:
    """Minutes the clock ran between `opened` and `until`."""
    total = dt.timedelta(0)
    if until <= opened:
        return 0.0
    for s, e in _running(opened, cal, tier, pauses):
        if s >= until:
            break
        total += min(e, until) - s
    return total.total_seconds() / 60
