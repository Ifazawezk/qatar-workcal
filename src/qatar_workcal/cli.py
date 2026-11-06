"""workcal command line."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter

from . import __version__
from .htmlview import page, write_page
from .ics import Event, write_ics
from .labour import article_73_warnings
from .output import format_table, write_csv
from .sla import TIERS, due, format_minutes, parse_duration
from .sprints import load_plan, plan_sprints
from .tickets import evaluate_all, load_tickets, parse_pauses, policies_from_config
from .workcal import QATAR, Config, WorkCalendar, parse_datetime

DATE_NOTE = (
    "Ramadan and Eid dates are calculated with the Umm al-Qura calendar. Qatar announces them "
    "after the crescent is sighted, so they can differ by a day; put the announced dates under "
    "overrides in the config."
)


def _when(moment: dt.datetime | None) -> str:
    return "-" if moment is None else f"{moment:%a %d %b %Y %H:%M}"


def _short(moment: dt.datetime | None) -> str:
    return "" if moment is None else f"{moment:%Y-%m-%d %H:%M}"


def cmd_holidays(args, cal: WorkCalendar) -> int:
    rows = [(h.date.isoformat(), f"{h.date:%a}", h.name) for h in cal.holidays(args.year)]
    print(format_table(["date", "day", "holiday"], rows))
    for start, end in cal.ramadan(args.year):
        hours = ", ".join(f"{a:%H:%M}-{b:%H:%M}" for a, b in cal.config.ramadan_hours)
        print(f"\nRamadan {start} to {end}, office hours {hours}")
    print(f"\n{DATE_NOTE}")
    if args.csv:
        write_csv(args.csv, ["date", "day", "holiday"], rows)
    if args.ics:
        one = dt.timedelta(days=1)
        events = [Event(f"holiday-{h.date}", h.name, h.date, h.date + one) for h in cal.holidays(args.year)]
        for start, end in cal.ramadan(args.year):
            events.append(Event(f"ramadan-{start}", "Ramadan office hours", start, end + one,
                                "Article 73: 6 hours a day, 36 a week"))
        write_ics(args.ics, events, f"Qatar holidays {args.year}")
    return 0


def cmd_due(args, cal: WorkCalendar) -> int:
    opened = parse_datetime(args.opened)
    minutes = parse_duration(args.sla)
    pauses = parse_pauses(";".join(args.pause or []))
    deadline = due(opened, minutes, cal, args.tier, pauses)
    print(f"opened   {_when(opened)} ({cal.describe(opened.date())})")
    unit = "business hours" if args.tier == "business" else "clock hours, 24x7"
    print(f"SLA      {format_minutes(minutes)} {unit}")
    for start, end in pauses:
        print(f"paused   {_when(start)} to {_when(end) if end else 'still paused'}")
    print(f"due      {_when(deadline) if deadline else 'not running, the ticket is paused'}")
    if deadline and args.tier == "business":
        day, skipped = opened.date(), []
        while day < deadline.date():
            day += dt.timedelta(days=1)
            if not cal.is_working_day(day):
                skipped.append(f"{day:%a %d %b} {cal.describe(day)}")
        if skipped:
            print("skipped  " + "\n         ".join(skipped))
    return 0


def _results(args, cal: WorkCalendar):
    now = parse_datetime(args.now) if args.now else dt.datetime.now(QATAR).replace(tzinfo=None, microsecond=0)
    policies = policies_from_config(cal.config.sla)
    return now, evaluate_all(load_tickets(args.tickets), cal, policies, now)


SLA_HEADERS = ["id", "priority", "tier", "opened", "due", "resolved", "used", "left", "state"]


def _sla_rows(results):
    return [
        (r.ticket.id, r.policy.name, r.policy.tier, _short(r.ticket.opened), _short(r.due),
         _short(r.ticket.resolved), format_minutes(r.used), format_minutes(r.remaining), r.state)
        for r in results
    ]


def cmd_sla(args, cal: WorkCalendar) -> int:
    now, results = _results(args, cal)
    rows = _sla_rows(results)
    print(format_table(SLA_HEADERS, rows))
    counts = Counter(r.state for r in results)
    summary = ", ".join(f"{counts[s]} {s}" for s in ("met", "breached", "at risk", "open", "paused") if counts[s])
    print(f"\n{len(results)} tickets at {_short(now)}: {summary}")
    if args.csv:
        write_csv(args.csv, SLA_HEADERS, rows)
    if args.ics:
        events = [
            Event(f"sla-{r.ticket.id}", f"SLA due {r.ticket.id} ({r.policy.name})", r.due,
                  r.due + dt.timedelta(minutes=15), f"{r.ticket.title}\nstate: {r.state}".strip())
            for r in results if r.due is not None
        ]
        write_ics(args.ics, events, "SLA due times")
    if args.html:
        classes = [r.state.replace(" ", "-") for r in results]
        notes = [f"{len(results)} tickets at {_short(now)}: {summary}", DATE_NOTE]
        write_page(args.html, page("SLA clock", notes, SLA_HEADERS, rows, classes))
    return 0


SPRINT_HEADERS = ["sprint", "start", "end", "ramadan days", "holidays", "capacity h", "release", "note"]


def _sprint_rows(sprints):
    rows = []
    for s in sprints:
        names = Counter(h.name for h in s.holidays)
        holidays = ", ".join(f"{n} x{c}" if c > 1 else n for n, c in names.items())
        rows.append((s.number, s.start.isoformat(), s.end.isoformat(), s.ramadan_days or "", holidays,
                     f"{s.capacity:g}", s.release.isoformat() if s.release else "none", s.release_note))
    return rows


def cmd_sprints(args, cal: WorkCalendar) -> int:
    plan, _ = load_plan(args.plan)
    sprints = plan_sprints(cal, plan)
    rows = _sprint_rows(sprints)
    print(format_table(SPRINT_HEADERS, rows))
    total = sum(s.capacity for s in sprints)
    print(f"\n{len(plan.members)} people, {len(sprints)} sprints of {plan.length} working days, "
          f"{total:g} hours in total (focus {plan.focus:g})")
    if args.csv:
        write_csv(args.csv, SPRINT_HEADERS, rows)
    if args.ics:
        one = dt.timedelta(days=1)
        events = []
        for sp in sprints:
            events.append(Event(f"sprint-{sp.number}-{sp.start}", f"Sprint {sp.number}", sp.start, sp.end + one,
                                f"{len(sp.days)} working days, {sp.capacity:g} hours"))
            if sp.release:
                events.append(Event(f"release-{sp.number}-{sp.release}", f"Release (sprint {sp.number})",
                                    sp.release, sp.release + one, sp.release_note))
            events += [Event(f"holiday-{h.date}", h.name, h.date, h.date + one) for h in sp.holidays]
        write_ics(args.ics, events, "Sprints")
    if args.html:
        classes = ["ramadan" if sp.ramadan_days else "" for sp in sprints]
        notes = [f"{len(plan.members)} people, {total:g} hours across {len(sprints)} sprints. "
                 "Shaded rows have Ramadan days.", DATE_NOTE]
        write_page(args.html, page("Sprint plan", notes, SPRINT_HEADERS, rows, classes, bar_column=5))
    return 0


def cmd_check(args, cal: WorkCalendar) -> int:
    warnings = article_73_warnings(cal.config)
    for w in warnings:
        print(w)
    if not warnings:
        print("Office hours and Ramadan hours are within the Article 73 limits.")
    return 1 if warnings else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="workcal", description="Qatar working calendar, SLA clock and sprint planner.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--config", help="calendar config (YAML): weekend, hours, holidays, overrides, sla")
    sub = p.add_subparsers(dest="command", required=True)

    h = sub.add_parser("holidays", help="public holidays and Ramadan for a year")
    h.add_argument("year", type=int)
    h.add_argument("--csv")
    h.add_argument("--ics", help="write the holidays and Ramadan as an iCalendar file")

    d = sub.add_parser("due", help="due time for one ticket")
    d.add_argument("opened", help='open time, e.g. "2026-03-19 15:00"')
    d.add_argument("sla", help="SLA length, e.g. 8h, 90m, 1h30m")
    d.add_argument("--tier", choices=TIERS, default="business")
    d.add_argument("--pause", action="append", metavar="START/END", help="pause the clock; leave END empty if still paused")

    s = sub.add_parser("sla", help="SLA state for a CSV of tickets")
    s.add_argument("tickets")
    s.add_argument("--now", help="evaluate as of this time (default: now in Qatar)")
    s.add_argument("--csv")
    s.add_argument("--ics", help="write each due time as an event")
    s.add_argument("--html")

    sp = sub.add_parser("sprints", help="sprint dates, capacity and release days from a plan file")
    sp.add_argument("plan")
    sp.add_argument("--csv")
    sp.add_argument("--ics", help="write sprints, release days and holidays as events")
    sp.add_argument("--html")

    sub.add_parser("check", help="check office hours against Labour Law Article 73")
    return p


COMMANDS = {
    "holidays": cmd_holidays,
    "due": cmd_due,
    "sla": cmd_sla,
    "sprints": cmd_sprints,
    "check": cmd_check,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cal = WorkCalendar(Config.load(args.config) if args.config else None)
        return COMMANDS[args.command](args, cal)
    except (OSError, ValueError, KeyError) as exc:
        print(f"workcal: {exc}", file=sys.stderr)
        return 2
