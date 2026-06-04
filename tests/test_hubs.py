"""Tests for the city-hub content assembly (W2 data layer).

A hub takes everything the engine + catalog know about one origin and shapes it
into the page's content: a verified hero, the full ranked list of trips by all-in
cost, and the cuts (cheapest, long-haul steals, by vibe). Display names use the
common-name override so an airport-city like AUA "Oranjestad" reads as "Aruba".
"""
import sqlite3

import pytest

from server.migrations import init_schema
from server import pairings, hubs


def _airport(conn, iata, city):
    conn.execute(
        "INSERT INTO airports (iata, city, state, region_us, lat, lng, rank_us) "
        "VALUES (?,?,?,?,?,?,?)",
        (iata, city, "TN", "SE", 36.1, -86.7, 12),
    )


def _dest(conn, iata, city, daily, region, vibes, best_months="[1]"):
    conn.execute(
        "INSERT INTO destinations (iata, city, country, country_code, region, "
        "vibes, passport_required, visa_required_us, best_months, "
        "avg_daily_cost_usd, safety_tier, currency, lat, lng, base_catch, "
        "novelty_score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iata, city, "Country", "CC", region, vibes, 1, 0, best_months, daily, 2,
         "USD", 0.0, 0.0, None, 3),
    )


def _fare(conn, origin, dest, price, nights=7):
    conn.execute(
        "INSERT INTO price_history (origin_iata, dest_iata, trip_nights, "
        "cheapest_price_usd, observed_date, source) VALUES (?,?,?,?, '2026-06-01','fli')",
        (origin, dest, nights, price),
    )


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    _airport(c, "BNA", "Nashville")
    # totals (air + 7*daily): GUA 683, MDE 821, LAS 1169, SOF 1100, AUA 1545
    _dest(c, "GUA", "Guatemala City", 45, "Latin America", '["history"]')
    _dest(c, "MDE", "Medellín", 50, "Latin America", '["city", "food"]')
    _dest(c, "LAS", "Las Vegas", 130, "North America", '["city", "nightlife"]')
    _dest(c, "SOF", "Sofia", 45, "Eastern Europe", '["city", "history"]')
    _dest(c, "AUA", "Oranjestad", 170, "Caribbean", '["beach"]')
    _fare(c, "BNA", "GUA", 368)
    _fare(c, "BNA", "MDE", 471)
    _fare(c, "BNA", "LAS", 259)
    _fare(c, "BNA", "SOF", 785)
    _fare(c, "BNA", "AUA", 355)
    c.commit()
    yield c
    c.close()


def test_build_hub_ranks_trips_by_total_cost(conn):
    hub = hubs.build_hub(conn, "BNA")
    assert hub["origin"] == "BNA"
    assert hub["origin_city"] == "Nashville"
    assert [t["iata"] for t in hub["trips"]] == ["GUA", "MDE", "SOF", "LAS", "AUA"]
    gua = hub["trips"][0]
    assert gua["total_usd"] == 683
    assert gua["airfare_usd"] == 368
    assert gua["vibes"] == ["history"]


def test_build_hub_applies_display_name_override(conn):
    hub = hubs.build_hub(conn, "BNA")
    aua = next(t for t in hub["trips"] if t["iata"] == "AUA")
    assert aua["city"] == "Aruba"  # catalog says "Oranjestad"


def test_build_hub_hero_uses_verified_pairing_and_override(conn):
    pairings.seed_pairings(conn)
    pairings.verify_all(conn, now="2026-06-04T00:00:00Z")
    hub = hubs.build_hub(conn, "BNA")
    assert hub["hero"]["headline"] == "A week in Medellín costs less than a week in Las Vegas."


def test_build_hub_hero_none_when_unverified(conn):
    # No verify run -> no served claim.
    hub = hubs.build_hub(conn, "BNA")
    assert hub["hero"] is None


def test_cheapest_trips(conn):
    hub = hubs.build_hub(conn, "BNA")
    assert [t["iata"] for t in hubs.cheapest_trips(hub, 2)] == ["GUA", "MDE"]


def test_by_vibe_returns_cheapest_with_that_vibe(conn):
    hub = hubs.build_hub(conn, "BNA")
    assert [t["iata"] for t in hubs.by_vibe(hub, "food", 3)] == ["MDE"]
    assert [t["iata"] for t in hubs.by_vibe(hub, "beach", 3)] == ["AUA"]


def test_long_haul_under_filters_overseas_below_benchmark(conn):
    hub = hubs.build_hub(conn, "BNA")
    # Sofia (overseas, $1100) beats the $1169 Vegas benchmark; LAS is domestic.
    assert [t["iata"] for t in hubs.long_haul_under(hub, 1169)] == ["SOF"]
