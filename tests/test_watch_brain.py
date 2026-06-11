from datetime import date, timedelta
from server.watch_brain import decide

T = date(2026, 6, 10)


def _series(*prices):
    """Build (iso_date, price) series ending yesterday."""
    n = len(prices)
    return [((T - timedelta(days=n - i)).isoformat(), p)
            for i, p in enumerate(prices)]


def test_night_one_never_alerts():
    assert decide(series=[], today_best=500, ceiling=None,
                  last_alert_at=None, today=T) is None


def test_drop_trigger_fires_from_night_two():
    d = decide(series=_series(500), today_best=430, ceiling=None,
               last_alert_at=None, today=T)          # 430 <= 0.88*500=440
    assert d and d["trigger"] == "drop"


def test_no_drop_when_above_factor():
    assert decide(series=_series(500), today_best=460, ceiling=None,
                  last_alert_at=None, today=T) is None


def test_drop_uses_trailing_14_low_not_alltime():
    # old all-time low 300 (15+ nights ago) must NOT suppress today's alert
    prices = [300] + [500] * 15                       # 300 is outside trailing 14
    d = decide(series=_series(*prices), today_best=430, ceiling=None,
               last_alert_at=None, today=T)
    assert d and d["trigger"] == "drop"


def test_percentile_needs_14_nights():
    prices = list(range(400, 400 + 13))               # 13 nights
    d = decide(series=_series(*prices), today_best=399, ceiling=None,
               last_alert_at=None, today=T)
    assert d is None or d["trigger"] != "percentile"


def test_percentile_fires_at_bottom_15():
    prices = [500 + i for i in range(20)]             # 20 nights, 500..519
    d = decide(series=_series(*prices), today_best=470, ceiling=None,
               last_alert_at=None, today=T)
    # 470 < all 20 -> bottom percentile; not a >=12% drop vs trailing low (506*.88=445)
    assert d and d["trigger"] == "percentile"


def test_ceiling_fires_anytime():
    d = decide(series=[], today_best=440, ceiling=450,
               last_alert_at=None, today=T)
    assert d and d["trigger"] == "ceiling"


def test_covenant_blocks_within_7_days():
    d = decide(series=_series(500), today_best=430, ceiling=None,
               last_alert_at=(T - timedelta(days=3)).isoformat(), today=T)
    assert d is None


def test_covenant_override_on_20pct_single_night_drop():
    d = decide(series=_series(500), today_best=395, ceiling=None,     # 395 < 0.8*500
               last_alert_at=(T - timedelta(days=3)).isoformat(), today=T)
    assert d and d["trigger"] == "drop" and d["override"] is True


def test_covenant_clears_after_7_days():
    d = decide(series=_series(500), today_best=430, ceiling=None,
               last_alert_at=(T - timedelta(days=8)).isoformat(), today=T)
    assert d and d["trigger"] == "drop"


def test_receipts_in_decision():
    prices = [500 + i for i in range(20)]
    d = decide(series=_series(*prices), today_best=470, ceiling=None,
               last_alert_at=None, today=T)
    assert d["nights_watched"] == 21                  # 20 prior + tonight
    assert 0 <= d["percentile"] <= 15
