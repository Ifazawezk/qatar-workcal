from qatar_workcal.labour import article_73_warnings
from qatar_workcal.workcal import Config


def test_defaults_are_within_article_73():
    assert article_73_warnings(Config()) == []


def test_long_ramadan_day_is_flagged():
    cfg = Config.from_dict({"ramadan_hours": ["08:00-12:00", "13:00-17:00"]})
    warnings = article_73_warnings(cfg)
    assert any("ramadan_hours: 8 hours a day" in w for w in warnings)
    assert any("40 hours a week" in w for w in warnings)


def test_no_break_and_six_day_week():
    cfg = Config.from_dict({"weekend": ["fri"], "hours": ["08:00-16:00"]})
    warnings = article_73_warnings(cfg)
    assert any("more than five hours" in w for w in warnings)
    assert any("at least one hour" in w for w in warnings)
    assert not any("48" in w for w in warnings)


def test_long_split_shift():
    cfg = Config.from_dict({"hours": ["06:00-10:00", "14:00-18:00"]})
    assert any("at most three hours" in w for w in article_73_warnings(cfg))
