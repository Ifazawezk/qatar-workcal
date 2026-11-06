from pathlib import Path

from qatar_workcal.cli import main

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "support-desk"


def test_support_desk_tickets(capsys):
    code = main(["--config", str(EXAMPLE / "config.yaml"), "sla", str(EXAMPLE / "tickets.csv"), "--now", "2026-06-04 12:00"])
    out = capsys.readouterr().out
    assert code == 0
    assert "42 tickets at 2026-06-04 12:00:" in out
    assert "paused" in out and "at risk" in out


def test_support_desk_sprints(capsys):
    code = main(["--config", str(EXAMPLE / "config.yaml"), "sprints", str(EXAMPLE / "team.yaml")])
    out = capsys.readouterr().out
    assert code == 0
    assert "6 people, 12 sprints of 10 working days" in out
    assert "Company day" in out and "Eid al-Fitr" in out


def test_example_config_passes_article_73(capsys):
    assert main(["--config", str(EXAMPLE / "config.yaml"), "check"]) == 0
