"""Tests for the budget-page pilot (programmatic SEO) — especially the
selectivity gate that keeps the lattice from going thin."""
import sqlite3

import pytest

from server.migrations import init_schema
from server import budget_pages, budget_render


def _airport(c, iata, city):
    c.execute("INSERT INTO airports (iata, city, state, region_us, lat, lng, rank_us) "
              "VALUES (?,?,?,?,?,?,?)", (iata, city, "TN", "SE", 36.1, -86.7, 12))


def _dest(c, iata, city, total, vibes="[]"):
    # daily=0 so the all-in total equals the airfare we record below.
    c.execute(
        "INSERT INTO destinations (iata, city, country, country_code, region, vibes, "
        "passport_required, visa_required_us, best_months, avg_daily_cost_usd, "
        "safety_tier, currency, lat, lng, base_catch, novelty_score) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iata, city, "Country", "CC", "Latin America", vibes, 1, 0, "[6]", 0, 2,
         "USD", 0.0, 0.0, None, 3))
    c.execute("INSERT INTO price_history (origin_iata, dest_iata, trip_nights, "
              "cheapest_price_usd, observed_date, source) VALUES ('BNA',?,7,?,'2026-06-01','fli')",
              (iata, total))


# 20 destinations engineered to exercise the two-sided gate:
#   <=$750: 2 (too thin -> suppress)   <=$1000: 9 (publish)
#   <=$1500: 14 = 70% (publish)        <=$2000: 19 = 95% (too broad -> suppress)
TOTALS = ([700, 710] + [760, 810, 860, 910, 960, 985, 990]
          + [1100, 1200, 1300, 1400, 1450] + [1600, 1700, 1800, 1900, 1950] + [2500])


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    _airport(c, "BNA", "Nashville")
    for i, total in enumerate(TOTALS):
        vibes = '["beach"]' if i in (3, 10) else '["city"]'
        _dest(c, f"D{i:02d}", f"City{i:02d}", total, vibes)
    c.commit()
    yield c
    c.close()


def test_gate_suppresses_thin_band(conn):
    assert budget_pages.build_budget_page(conn, "BNA", 750) is None  # only 2 qualify


def test_gate_suppresses_too_broad_band(conn):
    assert budget_pages.build_budget_page(conn, "BNA", 2000) is None  # 95% of catalog


def test_gate_publishes_constraining_bands(conn):
    p1000 = budget_pages.build_budget_page(conn, "BNA", 1000)
    p1500 = budget_pages.build_budget_page(conn, "BNA", 1500)
    assert p1000["count"] == 9
    assert p1500["count"] == 14
    # trips are under budget and sorted cheapest-first
    assert all(t["total_usd"] <= 1000 for t in p1000["trips"])
    assert p1000["trips"] == sorted(p1000["trips"], key=lambda t: t["total_usd"])


def test_published_bands(conn):
    assert budget_pages.published_bands(conn, "BNA") == [1000, 1500]


def test_intro_is_data_grounded_and_band_specific(conn):
    p1000 = budget_pages.build_budget_page(conn, "BNA", 1000)
    p1500 = budget_pages.build_budget_page(conn, "BNA", 1500)
    assert "9 destinations" in p1000["intro"]
    assert "$1,000" in p1000["intro"]
    assert p1000["trips"][0]["city"] in p1000["intro"]              # the floor
    assert p1000["trips"][-1]["city"] in p1000["intro"]            # a headliner (priciest under budget)
    # Sibling bands must NOT share the same "reaches" headliners (anti-cannibalization).
    assert p1000["trips"][-1]["city"] not in p1500["intro"]


def test_render_has_seo_freshness_and_internal_links(conn):
    p = budget_pages.build_budget_page(conn, "BNA", 1000)
    html = budget_render.render_budget_page(
        p, sibling_bands=[1000, 1500], freshness="2026-06-05")
    assert 'rel="canonical" href="https://promptiv.io/nashville/under-1000"' in html
    assert "<title>Trips under $1,000 from Nashville | Promptiv</title>" in html
    assert "Prices updated 2026-06-05." in html
    assert '/nashville/under-1500' in html          # sibling-band internal link
    assert 'href="/nashville"' in html              # link back to the hub
    assert 'href="/go"' in html                     # link to the tool
