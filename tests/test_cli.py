from qatar_workcal.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_holidays(capsys, tmp_path):
    code, out, _ = run(capsys, "holidays", "2026", "--csv", str(tmp_path / "h.csv"))
    assert code == 0
    assert "2026-03-22  Sun  Eid al-Fitr" in out
    assert "Ramadan 2026-02-18 to 2026-03-19" in out
    assert (tmp_path / "h.csv").read_text(encoding="utf-8").startswith("date,day,holiday")


def test_due_before_eid(capsys):
    code, out, _ = run(capsys, "due", "2026-03-19 15:00", "8h")
    assert code == 0
    assert "due      Wed 25 Mar 2026 16:00" in out
    assert "Sun 22 Mar Eid al-Fitr" in out


def test_due_24x7_and_pause(capsys):
    _, out, _ = run(capsys, "due", "2026-03-19 15:00", "4h", "--tier", "24x7", "--pause", "2026-03-19 16:00/2026-03-19 18:00")
    assert "due      Thu 19 Mar 2026 21:00" in out
    _, out, _ = run(capsys, "due", "2026-03-19 15:00", "4h", "--pause", "2026-03-19 15:30/")
    assert "still paused" in out and "not running" in out


def test_sla_file(capsys, tmp_path):
    tickets = tmp_path / "t.csv"
    tickets.write_text(
        "id,priority,opened,resolved,paused\n"
        "A,P2,2026-03-19 15:00,2026-03-25 10:00,\n"
        "B,P1,2026-03-19 15:00,,\n",
        encoding="utf-8",
    )
    code, out, _ = run(capsys, "sla", str(tickets), "--now", "2026-03-25 12:00", "--csv", str(tmp_path / "o.csv"))
    assert code == 0
    assert "2 tickets at 2026-03-25 12:00: 1 met, 1 breached" in out
    assert "A,P2,business" in (tmp_path / "o.csv").read_text(encoding="utf-8")


def test_sprints_with_config(capsys, tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("holidays:\n  - {date: 2026-01-13, name: Offsite}\n", encoding="utf-8")
    plan = tmp_path / "p.yaml"
    plan.write_text("start: 2026-01-04\ncount: 2\nmembers: [Noor, Sami]\n", encoding="utf-8")
    code, out, _ = run(capsys, "--config", str(cfg), "sprints", str(plan))
    assert code == 0
    assert "Offsite" in out
    assert "2 people, 2 sprints of 10 working days" in out


def test_check(capsys, tmp_path):
    assert run(capsys, "check")[0] == 0
    cfg = tmp_path / "c.yaml"
    cfg.write_text('ramadan_hours: ["08:00-12:00", "13:00-17:00"]\n', encoding="utf-8")
    code, out, _ = run(capsys, "--config", str(cfg), "check")
    assert code == 1 and "Article 73 allows 6" in out


def test_errors_exit_2(capsys, tmp_path):
    code, _, err = run(capsys, "due", "not a date", "8h")
    assert code == 2 and err.startswith("workcal:")
    code, _, err = run(capsys, "sla", str(tmp_path / "missing.csv"))
    assert code == 2
