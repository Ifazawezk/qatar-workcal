"""Support tickets: SLA policies, a CSV reader and per-ticket results."""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .sla import TIERS, Pause, due, elapsed, parse_duration
from .workcal import WorkCalendar, parse_datetime


@dataclass(frozen=True)
class Policy:
    name: str
    minutes: int
    tier: str = "business"


DEFAULT_POLICIES = {
    "P1": Policy("P1", 4 * 60, "24x7"),
    "P2": Policy("P2", 8 * 60),
    "P3": Policy("P3", 24 * 60),
    "P4": Policy("P4", 40 * 60),
}


def policies_from_config(raw: dict[str, Any] | None) -> dict[str, Policy]:
    """`sla:` in the config, for example {"P1": {"hours": "4h", "tier": "24x7"}}."""
    if not raw:
        return dict(DEFAULT_POLICIES)
    out = {}
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            spec = {"hours": spec}
        tier = str(spec.get("tier", "business"))
        if tier not in TIERS:
            raise ValueError(f"SLA {name}: tier must be one of {', '.join(TIERS)}")
        out[str(name)] = Policy(str(name), parse_duration(spec["hours"]), tier)
    return out


@dataclass
class Ticket:
    id: str
    priority: str
    opened: dt.datetime
    resolved: dt.datetime | None = None
    pauses: tuple[Pause, ...] = ()
    title: str = ""


@dataclass
class Result:
    ticket: Ticket
    policy: Policy
    due: dt.datetime | None
    used: float
    state: str

    @property
    def remaining(self) -> float:
        return self.policy.minutes - self.used


def parse_pauses(text: str) -> tuple[Pause, ...]:
    """"start/end; start/end" with an empty end for a pause that is still open."""
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        start, _, end = part.partition("/")
        out.append((parse_datetime(start), parse_datetime(end) if end.strip() else None))
    return tuple(out)


def load_tickets(path: str | Path) -> list[Ticket]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"id", "priority", "opened"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        tickets = []
        for n, row in enumerate(reader, start=2):
            try:
                tickets.append(Ticket(
                    id=row["id"].strip(),
                    priority=row["priority"].strip(),
                    opened=parse_datetime(row["opened"]),
                    resolved=parse_datetime(row["resolved"]) if (row.get("resolved") or "").strip() else None,
                    pauses=parse_pauses(row.get("paused", "")),
                    title=(row.get("title") or "").strip(),
                ))
            except ValueError as exc:
                raise ValueError(f"{path} line {n}: {exc}") from exc
    return tickets


def evaluate(ticket: Ticket, cal: WorkCalendar, policies: dict[str, Policy], now: dt.datetime) -> Result:
    if ticket.priority not in policies:
        raise ValueError(f"ticket {ticket.id}: no SLA for priority {ticket.priority!r}")
    policy = policies[ticket.priority]
    deadline = due(ticket.opened, policy.minutes, cal, policy.tier, ticket.pauses)
    end = ticket.resolved or now
    used = elapsed(ticket.opened, end, cal, policy.tier, ticket.pauses)
    if ticket.resolved is not None:
        state = "met" if deadline is None or ticket.resolved <= deadline else "breached"
    elif deadline is None:
        state = "paused"
    elif now > deadline:
        state = "breached"
    elif used >= 0.75 * policy.minutes:
        state = "at risk"
    else:
        state = "open"
    return Result(ticket, policy, deadline, used, state)


def evaluate_all(tickets: list[Ticket], cal: WorkCalendar, policies: dict[str, Policy], now: dt.datetime) -> list[Result]:
    return [evaluate(t, cal, policies, now) for t in tickets]
