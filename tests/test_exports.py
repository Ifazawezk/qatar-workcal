import datetime as dt

from qatar_workcal.cli import main
from qatar_workcal.htmlview import page
from qatar_workcal.ics import Event, to_ics


def test_ics_dates_times_and_escaping():
    text = to_ics([
        Event("a", "Eid al-Fitr", dt.date(2026, 3, 22), dt.date(2026, 3, 23)),
        Event("b", "SLA due QD-1, P2; urgent", dt.datetime(2026, 3, 25, 16), dt.datetime(2026, 3, 25, 16, 15)),
    ], now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert "DTSTART;VALUE=DATE:20260322\r\n" in text
    assert "DTSTART:20260325T130000Z\r\n" in text  # 16:00 in Doha is 13:00 UTC
    assert "SUMMARY:SLA due QD-1\\, P2\\; urgent" in text
    assert text.count("BEGIN:VEVENT") == 2 and text.endswith("END:VCALENDAR\r\n")


def test_ics_folds_long_lines():
    text = to_ics([Event("a", "x" * 200, dt.date(2026, 1, 1), dt.date(2026, 1, 2))], now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    assert "\r\n x" in text


def test_page_escapes_and_draws_bars():
    html = page("Plan <1>", ["note & more"], ["a", "h"], [("<b>", 10), ("c", 5)], ["", "ramadan"], bar_column=1)
    assert "Plan &lt;1&gt;" in html and "&lt;b&gt;" in html and "note &amp; more" in html
    assert 'style="width:160px"' in html and 'style="width:80px"' in html
    assert 'class="ramadan"' in html


def test_cli_writes_ics_and_html(capsys, tmp_path):
    assert main(["holidays", "2026", "--ics", str(tmp_path / "h.ics")]) == 0
    assert "SUMMARY:Ramadan office hours" in (tmp_path / "h.ics").read_text(encoding="utf-8")
    tickets = tmp_path / "t.csv"
    tickets.write_text("id,priority,opened,title\nA,P2,2026-03-19 15:00,Login fails\n", encoding="utf-8")
    assert main(["sla", str(tickets), "--now", "2026-03-25 12:00", "--ics", str(tmp_path / "s.ics"),
                 "--html", str(tmp_path / "s.html")]) == 0
    assert "DTSTART:20260325T130000Z" in (tmp_path / "s.ics").read_text(encoding="utf-8")
    assert "<td>open</td>" in (tmp_path / "s.html").read_text(encoding="utf-8")
    plan = tmp_path / "p.yaml"
    plan.write_text("start: 2026-03-01\ncount: 2\nmembers: [Noor]\n", encoding="utf-8")
    assert main(["sprints", str(plan), "--ics", str(tmp_path / "p.ics"), "--html", str(tmp_path / "p.html")]) == 0
    ics = (tmp_path / "p.ics").read_text(encoding="utf-8")
    assert "SUMMARY:Sprint 2" in ics and "SUMMARY:Eid al-Fitr" in ics
    assert 'class="ramadan"' in (tmp_path / "p.html").read_text(encoding="utf-8")
