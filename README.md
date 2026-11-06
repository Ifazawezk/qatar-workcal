# qatar-workcal

A working calendar for software teams in Qatar. It knows the Friday and Saturday weekend, the public holidays (both Eids come from the Hijri calendar), and the shorter working day in Ramadan. On top of that it works out SLA due times for support tickets and plans sprints with real team capacity.

A P2 ticket opened at 3pm on the last day of Ramadan 2026 with an 8 hour SLA gets one hour that day. The weekend and three days of Eid leave pass before the clock runs again, so it is due the following Wednesday:

```
$ workcal due "2026-03-19 15:00" 8h
opened   Thu 19 Mar 2026 15:00 (Ramadan hours)
SLA      8h00m business hours
due      Wed 25 Mar 2026 16:00
skipped  Fri 20 Mar weekend
         Sat 21 Mar weekend
         Sun 22 Mar Eid al-Fitr
         Mon 23 Mar Eid al-Fitr
         Tue 24 Mar Eid al-Fitr
```

## Install

Needs Python 3.10 or newer. From a clone:

```
pip install .
```

That gives you the `workcal` command. The only dependencies are hijridate (for Umm al-Qura dates) and PyYAML.

## Usage

### SLA clock

`due` takes an open time and an SLA (`8h`, `90m`, `1h30m`). Business hours are the default. `--tier 24x7` counts every minute, and `--pause START/END` stops the clock while you wait on the customer (leave END empty if the ticket is still paused).

```
$ workcal due "2026-03-19 15:00" 4h --tier 24x7 --pause "2026-03-19 16:00/2026-03-19 18:00"
opened   Thu 19 Mar 2026 15:00 (Ramadan hours)
SLA      4h00m clock hours, 24x7
paused   Thu 19 Mar 2026 16:00 to Thu 19 Mar 2026 18:00
due      Thu 19 Mar 2026 21:00
```

For a whole queue, put tickets in a CSV with `id,priority,opened,resolved,paused,title` (only the first three are required) and map priorities to SLAs in the config. This is the generated support desk in `examples/support-desk`, cut down to the rows around Eid al-Fitr and the end of the file:

```
$ workcal --config config.yaml sla tickets.csv --now "2026-06-04 12:00"
id       priority  tier      opened            due               resolved          used    left    state
-------  --------  --------  ----------------  ----------------  ----------------  ------  ------  --------
QD-1014  P2        business  2026-03-18 02:45  2026-03-19 11:00  2026-03-18 11:00  2h00m   6h00m   met
QD-1015  P2        business  2026-03-19 15:00  2026-03-25 16:00  2026-03-25 15:12  7h12m   0h48m   met
QD-1016  P1        24x7      2026-03-21 22:40  2026-03-22 02:40  2026-03-22 01:28  2h48m   1h12m   met
...
QD-1039  P3        business  2026-06-02 10:00                                      7h00m   17h00m  paused
QD-1040  P3        business  2026-06-02 16:35  2026-06-09 11:12                    4h48m   19h12m  open
QD-1041  P2        business  2026-06-03 13:30  2026-06-04 13:30                    7h30m   0h30m   at risk
QD-1042  P3        business  2026-06-03 18:00  2026-06-08 17:00                    4h00m   20h00m  open

42 tickets at 2026-06-04 12:00: 27 met, 10 breached, 1 at risk, 3 open, 1 paused
```

A ticket is "at risk" once it has used 75% of its SLA.

### Sprints and releases

A plan file lists the start date, sprint length in working days, a focus factor and the team. Leave can be a date or a `from..to` range, and `allocation: 0.5` is a half-time member. Capacity drops in Ramadan (six hours a day instead of eight) and on leave days.

Release days default to Sunday to Wednesday, because a Thursday release leaves nobody around for the weekend. A release also moves earlier when a holiday comes right after it (`freeze_days`, default 1).

```
$ workcal --config config.yaml sprints team.yaml
sprint  start       end         ramadan days  holidays            capacity h  release     note
------  ----------  ----------  ------------  ------------------  ----------  ----------  ------------------------------------------------
1       2026-01-04  2026-01-15                                    352         2026-01-14  moved from Thu 15 Jan: no releases on Thursday
2       2026-01-18  2026-01-29                                    352         2026-01-28  moved from Thu 29 Jan: no releases on Thursday
3       2026-02-01  2026-02-15                National Sport Day  326.4       2026-02-15
4       2026-02-16  2026-03-01  8                                 281.6       2026-03-01
5       2026-03-02  2026-03-15  10                                259.2       2026-03-15
6       2026-03-16  2026-04-01  4             Eid al-Fitr x3      284.8       2026-03-31  moved from Wed 01 Apr: Company day on Thu 02 Apr
7       2026-04-05  2026-04-16                                    352         2026-04-15  moved from Thu 16 Apr: no releases on Thursday
8       2026-04-19  2026-04-30                                    352         2026-04-29  moved from Thu 30 Apr: no releases on Thursday
9       2026-05-03  2026-05-14                                    352         2026-05-13  moved from Thu 14 May: no releases on Thursday
10      2026-05-17  2026-06-02                Eid al-Adha x3      320         2026-06-02
11      2026-06-03  2026-06-16                                    339.2       2026-06-16
12      2026-06-17  2026-06-30                                    352         2026-06-30

6 people, 12 sprints of 10 working days, 3923.2 hours in total (focus 0.8)
```

### Holidays

```
$ workcal holidays 2026
date        day  holiday
----------  ---  ------------------
2026-02-10  Tue  National Sport Day
2026-03-22  Sun  Eid al-Fitr
2026-03-23  Mon  Eid al-Fitr
2026-03-24  Tue  Eid al-Fitr
2026-05-27  Wed  Eid al-Adha
2026-05-28  Thu  Eid al-Adha
2026-05-31  Sun  Eid al-Adha
2026-12-18  Fri  National Day

Ramadan 2026-02-18 to 2026-03-19, office hours 09:00-12:00, 13:00-16:00
```

Eid al-Fitr 2026 starts on a Friday, so the leave lands on Sunday to Tuesday. Article 78 of the Labour Law gives three working days for each Eid and one for National Day, and that is how the dates are counted here.

### Output files

`holidays`, `sla` and `sprints` take `--csv FILE` and `--ics FILE`. `sla` and `sprints` also take `--html FILE` for a single page you can open or share. The iCalendar file has all-day events for holidays, Ramadan, sprints and release days, and a timed event at each SLA due time.

`workcal check` compares your office hours with Article 73 (8 hours a day and 48 a week, 6 and 36 in Ramadan, breaks of one to three hours, no more than five hours in a row) and exits with 1 if something is over.

## Config

Everything is optional. Apart from `holidays` and `overrides`, the values below are the defaults.

```yaml
weekend: [fri, sat]
hours: ["08:00-12:00", "13:00-17:00"]
ramadan_hours: ["09:00-12:00", "13:00-16:00"]
sport_day: true          # second Tuesday of February
eid_length: 3            # working days per Eid
holidays:                # the three days Article 78 leaves to the employer
  - {date: 2026-04-02, name: Company day}
remove: []               # drop a holiday your company works through
overrides:               # announced dates, once they are out
  eid_al_adha: 2026-05-26
sla:
  P1: {hours: 4h, tier: 24x7}
  P2: {hours: 8h}
  P3: {hours: 24h}
  P4: {hours: 40h}
```

All times are Qatar local time. Input with an offset such as `Z` or `+00:00` is converted to UTC+3.

To rebuild the example data: `python examples/support-desk/make_data.py`. The tickets, team and company are made up.

## Limits

This is a planning tool, not legal advice. Ramadan and the Eids are calculated with the Umm al-Qura calendar, and Qatar announces them after the crescent is sighted, so the real dates can be a day off; use `overrides` when the announcement is out. Labour rules and holiday announcements change, and many employers give longer Eid breaks than the legal minimum, so confirm anything that matters with the Ministry of Labour. The Article 73 limits apply to each worker; a desk that is open longer than that needs shifts, which this tool does not model.

## License

MIT
