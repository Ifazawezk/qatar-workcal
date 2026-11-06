"""Minimal iCalendar (RFC 5545) writer for all-day and timed events."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from .workcal import QATAR


@dataclass
class Event:
    uid: str
    summary: str
    start: dt.date | dt.datetime
    end: dt.date | dt.datetime
    description: str = ""


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Split lines longer than 75 octets, continuing with a leading space."""
    out, current = [], ""
    for ch in line:
        limit = 75 if not out else 74
        if len((current + ch).encode("utf-8")) > limit:
            out.append(current)
            current = ch
        else:
            current += ch
    out.append(current)
    return [out[0]] + [" " + part for part in out[1:]]


def _stamp(value: dt.date | dt.datetime, name: str) -> str:
    if isinstance(value, dt.datetime):
        utc = value.replace(tzinfo=QATAR).astimezone(dt.timezone.utc)
        return f"{name}:{utc:%Y%m%dT%H%M%SZ}"
    return f"{name};VALUE=DATE:{value:%Y%m%d}"


def to_ics(events: list[Event], name: str = "workcal", now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    stamp = f"{now.astimezone(dt.timezone.utc):%Y%m%dT%H%M%SZ}"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//qatar-workcal//EN", "CALSCALE:GREGORIAN",
             f"X-WR-CALNAME:{_escape(name)}"]
    for e in events:
        lines += ["BEGIN:VEVENT", f"UID:{e.uid}@qatar-workcal", f"DTSTAMP:{stamp}",
                  _stamp(e.start, "DTSTART"), _stamp(e.end, "DTEND"), f"SUMMARY:{_escape(e.summary)}"]
        if e.description:
            lines.append(f"DESCRIPTION:{_escape(e.description)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"


def write_ics(path: str | Path, events: list[Event], name: str = "workcal") -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(to_ics(events, name))
