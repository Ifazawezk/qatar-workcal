"""Generate the support desk example: a calendar config, tickets and a sprint plan.

Everything here is made up. Run from the repo root:

    python examples/support-desk/make_data.py
"""
from __future__ import annotations

import csv
import datetime as dt
import random
from pathlib import Path

from qatar_workcal.sla import due
from qatar_workcal.tickets import policies_from_config
from qatar_workcal.workcal import Config, WorkCalendar

HERE = Path(__file__).parent
NOW = dt.datetime(2026, 6, 4, 12, 0)

CONFIG = """\
# Office calendar for a made-up software support desk in Doha.
weekend: [fri, sat]
hours: ["08:00-12:00", "13:00-17:00"]
ramadan_hours: ["09:00-12:00", "13:00-16:00"]
sport_day: true
holidays:
  # Article 78 leaves three paid days to the employer.
  - {date: 2026-04-02, name: Company day}
# Put announced dates here once they are out, for example:
# overrides:
#   eid_al_adha: 2026-05-26
sla:
  P1: {hours: 4h, tier: 24x7}
  P2: {hours: 8h}
  P3: {hours: 24h}
  P4: {hours: 40h}
"""

TEAM = """\
# Two-week sprints for the same made-up team.
start: 2026-01-04
length: 10
count: 12
focus: 0.8
release_days: [sun, mon, tue, wed]
freeze_days: 1
members:
  - name: Noor
  - name: Sami
    leave: ["2026-03-15..2026-03-26"]
  - name: Hana
    leave: ["2026-05-24..2026-06-04"]
  - name: Yousef
  - name: Maya
    allocation: 0.5
  - name: Karim
    leave: ["2026-02-08..2026-02-12", "2026-05-31"]
"""

TITLES = [
    "Login page times out", "Invoice PDF shows wrong VAT line", "Password reset email not received",
    "Report export stuck at 99%", "Mobile app crashes on Arabic search", "API returns 500 on bulk upload",
    "SSO redirect loop", "Slow dashboard load", "Wrong timezone on audit log", "Webhook retries flooding",
    "User cannot change phone number", "CSV import drops last row", "Dark mode text unreadable",
    "Push notifications delayed", "Payment page shows blank screen", "Role permissions not saved",
]

# Tickets placed on purpose around Ramadan and the two Eids.
FIXED = [
    ("P2", dt.datetime(2026, 3, 19, 15, 0), 0.9, "Customer portal down before Eid", ""),
    ("P1", dt.datetime(2026, 3, 21, 22, 40), 0.7, "Payments failing on Eid night", ""),
    ("P3", dt.datetime(2026, 2, 18, 9, 30), 1.1, "First day of Ramadan: rota page wrong", ""),
    ("P2", dt.datetime(2026, 5, 26, 16, 30), 0.6, "Release notes missing before Eid al-Adha", ""),
    ("P3", dt.datetime(2026, 6, 2, 10, 0), 2.0, "Waiting on customer logs", "2026-06-03 09:00/"),
    ("P2", dt.datetime(2026, 6, 3, 13, 30), 2.0, "Slow search after release", ""),
]


def main() -> None:
    (HERE / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (HERE / "team.yaml").write_text(TEAM, encoding="utf-8")
    cal = WorkCalendar(Config.load(HERE / "config.yaml"))
    policies = policies_from_config(cal.config.sla)
    rng = random.Random(2026)

    rows = list(FIXED)
    start = dt.datetime(2026, 2, 1)
    for n in range(36):
        opened = start + dt.timedelta(minutes=rng.randrange(0, 123 * 24 * 60))
        opened = opened.replace(minute=opened.minute - opened.minute % 5)
        priority = rng.choices(["P1", "P2", "P3", "P4"], weights=[1, 4, 6, 3])[0]
        share = rng.uniform(0.2, 1.35)
        pause = ""
        if priority in ("P3", "P4") and rng.random() < 0.3:
            pause_start = due(opened, int(policies[priority].minutes * 0.2), cal, policies[priority].tier)
            pause_end = pause_start + dt.timedelta(hours=rng.choice([3, 20, 48]))
            pause = f"{pause_start:%Y-%m-%d %H:%M}/{pause_end:%Y-%m-%d %H:%M}"
        rows.append((priority, opened, share, rng.choice(TITLES), pause))

    out = []
    for n, (priority, opened, share, title, pause) in enumerate(sorted(rows, key=lambda r: r[1])):
        policy = policies[priority]
        pauses = []
        if pause:
            a, b = pause.split("/")
            pauses = [(dt.datetime.fromisoformat(a), dt.datetime.fromisoformat(b) if b else None)]
        resolved = due(opened, int(policy.minutes * share), cal, policy.tier, pauses)
        resolved_text = f"{resolved:%Y-%m-%d %H:%M}" if resolved and resolved <= NOW else ""
        out.append((f"QD-{1001 + n}", priority, f"{opened:%Y-%m-%d %H:%M}", resolved_text, pause, title))

    with open(HERE / "tickets.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "priority", "opened", "resolved", "paused", "title"])
        writer.writerows(out)
    print(f"wrote {len(out)} tickets, config.yaml and team.yaml to {HERE}")


if __name__ == "__main__":
    main()
