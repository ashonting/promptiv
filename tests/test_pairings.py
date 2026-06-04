"""Tests for the pairing engine + fact monitor (W1).

The pairing (origin -> cheap dest, anchor dest) is the durable creative; the
dollar figures are facts re-checked on every fare refresh. These tests pin down
the verification gate: a claim is only served when the data actually backs it.
"""
import sqlite3

import pytest

from server.migrations import init_schema
from server import pairings
from server.email_client import send_pairing_alert


def _dest(conn, iata, city, daily):
    """Insert a destination with a given avg daily on-ground cost."""
    conn.execute(
        "INSERT INTO destinations (iata, city, country, country_code, region, "
        "vibes, passport_required, visa_required_us, best_months, "
        "avg_daily_cost_usd, safety_tier, currency, lat, lng, base_catch, "
        "novelty_score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iata, city, "Country", "CC", "LA", "[]", 1, 0, "[1]", daily, 2,
         "USD", 0.0, 0.0, None, 3),
    )


def _fare(conn, origin, dest, price, nights=7, day="2026-06-01"):
    """Record a cheapest-fare observation for a route in price_history."""
    conn.execute(
        "INSERT INTO price_history (origin_iata, dest_iata, trip_nights, "
        "cheapest_price_usd, observed_date, source) VALUES (?,?,?,?,?,'fli')",
        (origin, dest, nights, price, day),
    )


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    # Medellín: cheap to fly ($471) and cheap on the ground ($50/day).
    _dest(c, "MDE", "Medellín", 50)
    # Las Vegas: cheap to fly ($259) but pricey on the ground ($130/day).
    _dest(c, "LAS", "Las Vegas", 130)
    _fare(c, "BNA", "MDE", 471)
    _fare(c, "BNA", "LAS", 259)
    c.commit()
    yield c
    c.close()


def test_total_cost_is_airfare_plus_week_on_ground(conn):
    # 471 + 7*50 = 821
    assert pairings.total_cost(conn, "BNA", "MDE") == 821
    # 259 + 7*130 = 1169  (the whole point: Vegas is cheaper to FLY, dearer to BE)
    assert pairings.total_cost(conn, "BNA", "LAS") == 1169


def test_total_cost_none_when_no_fare(conn):
    assert pairings.total_cost(conn, "BNA", "XXX") is None


def test_seed_pairings_is_idempotent(conn):
    pairings.seed_pairings(conn)
    pairings.seed_pairings(conn)  # second call must not duplicate or clobber
    n = conn.execute("SELECT COUNT(*) FROM city_pairings").fetchone()[0]
    assert n == len(pairings.CURATED_PAIRINGS)
    row = conn.execute(
        "SELECT cheap_iata, anchor_iata FROM city_pairings WHERE origin_iata='BNA'"
    ).fetchone()
    assert row == ("MDE", "LAS")


def test_verify_marks_true_false_and_unknown(conn):
    # Verified: cheap (821) < anchor (1169), margin 348.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, verified) VALUES ('BNA','MDE','LAS',7,0)")
    # Broken: origin XXX with the SAME two dests but reversed roles. Needs its own
    # fares (price_history is keyed by origin), so cheap (LAS 1169) > anchor
    # (MDE 821), margin -348.
    _fare(conn, "XXX", "LAS", 259)
    _fare(conn, "XXX", "MDE", 471)
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, verified) VALUES ('XXX','LAS','MDE',7,0)")
    # Unknown: anchor has no fare data, no claim possible.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, verified) VALUES ('YYY','MDE','ZZZ',7,0)")

    summary = pairings.verify_all(conn, now="2026-06-04T00:00:00Z")
    assert summary == {"verified": 1, "broken": 1, "unknown": 1}

    assert conn.execute("SELECT verified, margin_usd FROM city_pairings WHERE origin_iata='BNA'").fetchone() == (1, 348)
    assert conn.execute("SELECT verified, margin_usd FROM city_pairings WHERE origin_iata='XXX'").fetchone() == (0, -348)
    assert conn.execute("SELECT verified, margin_usd FROM city_pairings WHERE origin_iata='YYY'").fetchone() == (0, None)


def test_get_headline_gated_on_verified(conn):
    pairings.seed_pairings(conn)
    # Before verification, nothing is served — even with a real pairing row.
    assert pairings.get_headline(conn, "BNA") is None

    pairings.verify_all(conn, now="2026-06-04T00:00:00Z")
    hl = pairings.get_headline(conn, "BNA")
    assert hl is not None
    assert hl["headline"] == "A week in Medellín costs less than a week in Las Vegas."
    assert hl["margin_usd"] == 348
    assert hl["cheap_total_usd"] == 821
    # An origin whose pairing lacks fare data stays unserved.
    assert pairings.get_headline(conn, "JFK") is None


def test_at_risk_flags_broken_and_thin_not_healthy(conn):
    # Healthy: verified, fat margin -> excluded.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, cheap_total_usd, anchor_total_usd, margin_usd, verified) VALUES ('AAA','MDE','LAS',7,800,1200,400,1)")
    # Thin: verified but margin under the threshold -> flagged.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, cheap_total_usd, anchor_total_usd, margin_usd, verified) VALUES ('BBB','MDE','LAS',7,1000,1040,40,1)")
    # Broken: both priced, claim false -> flagged.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, cheap_total_usd, anchor_total_usd, margin_usd, verified) VALUES ('CCC','MDE','LAS',7,1200,800,-400,0)")
    # No data: excluded — nothing to re-pair until fares arrive.
    conn.execute("INSERT INTO city_pairings (origin_iata, cheap_iata, anchor_iata, trip_nights, verified) VALUES ('DDD','MDE','LAS',7,0)")

    flagged = pairings.at_risk(conn)
    assert {f["origin"]: f["reason"] for f in flagged} == {"BBB": "thin_margin", "CCC": "broken"}


def test_pairing_alert_noop_when_nothing_at_risk():
    # Empty risk list must never send — no recipient lookup, no network.
    assert send_pairing_alert([]) is None


def test_pairing_alert_skipped_without_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "k")
    monkeypatch.setenv("RESEND_FROM", "from@example.com")
    monkeypatch.delenv("PAIRING_ALERT_TO", raising=False)
    monkeypatch.delenv("RESEND_REPLY_TO", raising=False)
    flagged = [{"origin": "BNA", "cheap_iata": "MDE", "anchor_iata": "LAS",
                "margin_usd": -10, "reason": "broken"}]
    assert send_pairing_alert(flagged) is None


def test_pairing_alert_sends_with_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "k")
    monkeypatch.setenv("RESEND_FROM", "from@example.com")
    sent = {}

    import resend

    def fake_send(payload):
        sent.update(payload)
        return {"id": "stub"}

    monkeypatch.setattr(resend.Emails, "send", fake_send)
    flagged = [{"origin": "BNA", "cheap_iata": "MDE", "anchor_iata": "LAS",
                "margin_usd": -10, "reason": "broken"}]
    resp = send_pairing_alert(flagged, to_email="ops@example.com")
    assert resp == {"id": "stub"}
    assert sent["to"] == ["ops@example.com"]
    assert "1 pairing claim(s)" in sent["subject"]
    assert "BNA: MDE vs LAS" in sent["text"]
