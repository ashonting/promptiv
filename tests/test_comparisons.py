"""Tests for the comparison pages — especially the robust-flip gate."""
import json
import sqlite3

import pytest

from server.migrations import init_schema
from server import comparisons, comparison_render


def _dest(c, iata, city, daily):
    c.execute(
        "INSERT INTO destinations (iata, city, country, country_code, region, vibes, "
        "passport_required, visa_required_us, best_months, avg_daily_cost_usd, "
        "safety_tier, currency, lat, lng, base_catch, novelty_score) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iata, city, "Country", "CC", "LA", "[]", 1, 0, "[1]", daily, 2,
         "USD", 0.0, 0.0, None, 3))


def _ph(c, origin, dest, price):
    c.execute("INSERT INTO price_history (origin_iata, dest_iata, trip_nights, "
              "cheapest_price_usd, observed_date, source) VALUES (?,?,7,?, '2026-06-01','fli')",
              (origin, dest, price))


@pytest.fixture
def conn(temp_db_path, monkeypatch):
    monkeypatch.setattr(comparisons, "MIN_ROBUST", 3)  # 3-origin fixture
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    _dest(c, "ANC", "Anchorton", 130)   # anchor: dear on the ground
    _dest(c, "CHP", "Cheapville", 50)    # winner: cheap on the ground, flip from all
    _dest(c, "WOB", "Wobbleton", 50)     # winner typically, but not robust
    for o in ("O1", "O2", "O3"):
        _ph(c, o, "ANC", 250)            # anchor total 250 + 910 = 1160 from all
        _ph(c, o, "CHP", 400)            # cheap total 400 + 350 = 750 from all (wins 3)
    _ph(c, "O1", "WOB", 400)             # 750 < 1160 (win)
    _ph(c, "O2", "WOB", 400)             # 750 < 1160 (win)
    _ph(c, "O3", "WOB", 1100)            # 1450 > 1160 (lose) -> wins 2 of 3
    c.commit()
    yield c
    c.close()


def test_typical_total_is_median_airfare_plus_week(conn):
    chp = {"iata": "CHP", "daily": 50}
    assert comparisons.typical_total(conn, chp) == (400, 750)


def test_robust_flip_publishes(conn):
    cmp = comparisons.build_comparison(conn, "CHP", "ANC", "angle")
    assert cmp is not None
    assert cmp["cheap"]["total"] == 750 and cmp["anchor"]["total"] == 1160
    assert cmp["margin"] == 410
    assert cmp["wins"] == 3 and cmp["origins"] == 3
    assert cmp["slug"] == "cheapville-vs-anchorton"


def test_non_robust_flip_is_gated(conn):
    # Wobbleton wins typically (median total 750 < 1160) but only from 2 of 3
    # origins, so with MIN_ROBUST=3 it must NOT publish.
    assert comparisons.build_comparison(conn, "WOB", "ANC") is None


def test_false_flip_is_gated(conn):
    # Reversed: the anchor isn't actually cheaper, so no page.
    assert comparisons.build_comparison(conn, "ANC", "CHP") is None


def test_render_has_seo_breakdown_proof_and_breadcrumb_no_offers(conn):
    cmp = comparisons.build_comparison(conn, "CHP", "ANC", "Cheap beats dear.")
    html = comparison_render.render_comparison(cmp, others=[], freshness="2026-06-05")
    assert 'rel="canonical" href="https://dashaway.io/vs/cheapville-vs-anchorton"' in html
    assert "which week costs less?" in html
    assert "Cheaper from <b>3 of 3</b>" in html       # the robustness proof
    assert "Prices updated 2026-06-05." in html
    assert '"BreadcrumbList"' in html and "application/ld+json" in html
    assert "Offer" not in html and '"price"' not in html and "Product" not in html
