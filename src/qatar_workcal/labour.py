"""Check office hours against Article 73 of the Labour Law (Law No. 14 of 2004).

Article 73 caps ordinary hours at 48 a week and 8 a day, and at 36 a week and 6 a
day in Ramadan. Work must include one or more breaks of one to three hours in
total, which are not counted as working time, and nobody works more than five
hours in a row. These limits apply to each worker, so a support desk open longer
than this needs shifts. Senior staff and some roles are excluded by Article 76.
"""
from __future__ import annotations

from .workcal import Config, Span, span_hours


def _minutes(t) -> int:
    return t.hour * 60 + t.minute


def _day_warnings(label: str, spans: tuple[Span, ...], daily_cap: float, weekly_cap: float, workdays: int) -> list[str]:
    out = []
    hours = span_hours(spans)
    if hours > daily_cap:
        out.append(f"{label}: {hours:g} hours a day, Article 73 allows {daily_cap:g}")
    if hours * workdays > weekly_cap:
        out.append(f"{label}: {hours * workdays:g} hours a week over {workdays} days, Article 73 allows {weekly_cap:g}")
    for start, end in spans:
        if _minutes(end) - _minutes(start) > 5 * 60:
            out.append(f"{label}: {start:%H:%M}-{end:%H:%M} is more than five hours without a break")
    ordered = sorted(spans)
    breaks = sum(_minutes(b[0]) - _minutes(a[1]) for a, b in zip(ordered, ordered[1:]))
    if hours > 5 and breaks < 60:
        out.append(f"{label}: breaks add up to {breaks} minutes, Article 73 asks for at least one hour")
    if breaks > 180:
        out.append(f"{label}: breaks add up to {breaks} minutes, Article 73 allows at most three hours")
    return out


def article_73_warnings(config: Config) -> list[str]:
    workdays = 7 - len(config.weekend)
    return (
        _day_warnings("hours", config.hours, 8, 48, workdays)
        + _day_warnings("ramadan_hours", config.ramadan_hours, 6, 36, workdays)
    )
