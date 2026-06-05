"""Tests for the weekly digest composer (W4) — the anti-staleness logic.

Covers the three freshness levers: trailing-window pricing, the rotating weekly
lens, and the gated deal-alerts (dormant until a route has enough history).
"""
import datetime
import sqlite3
from unittest.mock import patch

import pytest

from server.migrations import init_schema
from server import pairings, hubs, digest, db


def _airport(c, iata, city):
    c.execute("INSERT INTO airports (iata, city, state, region_us, lat, lng, rank_us) "
              "VALUES (?,?,?,?,?,?,?)", (iata, city, "TN", "SE", 36.1, -86.7, 12))


def _dest(c, iata, city, daily, vibes, best_months, region="Latin America"):
    c.execute(
        "INSERT INTO destinations (iata, city, country, country_code, region, vibes, "
        "passport_required, visa_required_us, best_months, avg_daily_cost_usd, "
        "safety_tier, currency, lat, lng, base_catch, novelty_score) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iata, city, "Country", "CC", region, vibes, 1, 0, best_months, daily, 2,
         "USD", 0.0, 0.0, None, 3))


def _ph(c, dest, price, day, origin="BNA", nights=7):
    c.execute("INSERT INTO price_history (origin_iata, dest_iata, trip_nights, "
              "cheapest_price_usd, observed_date, source) VALUES (?,?,?,?,?,'fli')",
              (origin, dest, nights, price, day))


AS_OF = datetime.date(2026, 6, 3)
WEEK = [(AS_OF - datetime.timedelta(days=i)).isoformat() for i in range(7)]  # last 7 days


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    _airport(c, "BNA", "Nashville")
    # cheap pairing legs + a mix of vibes for the lenses
    _dest(c, "MDE", "Medellín", 50, '["city","food"]', "[1,2,3]")
    _dest(c, "LAS", "Las Vegas", 130, '["city","nightlife"]', "[3,4,5]", region="North America")
    _dest(c, "CTG", "Cartagena", 75, '["beach","food"]', "[12,1,2]")
    _dest(c, "SJU", "San Juan", 100, '["beach"]', "[6,7,8]")
    _dest(c, "SOF", "Sofia", 45, '["city","history"]', "[5,6,7]", region="Eastern Europe")
    for day in WEEK:  # full recent week so the trailing window has data
        _ph(c, "MDE", 471, day); _ph(c, "LAS", 259, day); _ph(c, "CTG", 409, day)
        _ph(c, "SJU", 176, day); _ph(c, "SOF", 785, day)
    c.commit()
    pairings.seed_pairings(c)
    pairings.verify_all(c, now="2026-06-03T00:00:00Z")
    yield c
    c.close()


def test_lens_rotates_through_a_full_cycle_by_week():
    # Five consecutive ISO weeks must hit five distinct lenses (a full rotation).
    keys = []
    for i in range(len(digest.LENSES)):
        d = datetime.date(2026, 6, 1) + datetime.timedelta(weeks=i)
        keys.append(digest.pick_lens(d)["key"])
    assert len(set(keys)) == len(digest.LENSES)


def test_build_hub_since_uses_recent_fares_not_all_time_floor(conn):
    # MDE was dirt cheap long ago, pricey this week. All-time floor sees the old
    # low; the trailing window must see the recent (higher) fare.
    _ph(conn, "MDE", 150, "2026-04-01")  # old outlier
    conn.commit()
    all_time = {t["iata"]: t["airfare_usd"] for t in hubs.build_hub(conn, "BNA")["trips"]}
    windowed = {t["iata"]: t["airfare_usd"] for t in hubs.build_hub(conn, "BNA", since=WEEK[-1])["trips"]}
    assert all_time["MDE"] == 150          # all-time floor includes the old low
    assert windowed["MDE"] == 471          # window ignores it


def test_in_season_lens_filters_by_month(conn):
    hub = hubs.build_hub(conn, "BNA", since=WEEK[-1])
    # SJU is in season in June ([6,7,8]); MDE ([1,2,3]) is not.
    june = digest._lens_picks("in_season", hub, datetime.date(2026, 6, 3))
    assert "SJU" in [t["iata"] for t in june]
    assert "MDE" not in [t["iata"] for t in june]


def test_deals_gated_until_enough_history(conn):
    # Only 7 days of history so far -> nothing is trustworthy yet.
    assert digest.detect_deals(conn, "BNA", AS_OF) == []


def test_deal_fires_once_history_is_deep_and_price_drops(conn):
    # 20 days of history for a new route at $1000, then a recent drop to $800.
    for i in range(6, 21):  # days -20..-6 at the normal price
        _ph(conn, "CUN", 1000, (AS_OF - datetime.timedelta(days=i)).isoformat())
    for i in range(0, 6):   # last 6 days at the deal price
        _ph(conn, "CUN", 800, (AS_OF - datetime.timedelta(days=i)).isoformat())
    _dest(conn, "CUN", "Cancún", 110, '["beach"]', "[12,1,2,3]")
    conn.commit()
    deals = {d["iata"]: d for d in digest.detect_deals(conn, "BNA", AS_OF)}
    assert "CUN" in deals
    assert deals["CUN"]["pct"] == 20  # 800 is 20% under the 1000 normal


def test_compose_returns_subject_html_text(conn):
    em = digest.compose_city_email(conn, "Nashville", as_of=AS_OF, week_index=0)
    assert em["subject"] == "This week's cheapest trips from Nashville"
    assert "Medellín" in em["html"]
    assert "Unsubscribe" in em["html"]
    assert em["text"].strip().startswith("This week's cheapest trips from Nashville")


def test_lens_falls_back_to_cheapest_when_cut_is_thin(conn):
    # Force the beach lens (index 1) but the only beach dests are CTG + SJU (2 < 3),
    # so it must fall back to the cheapest subject.
    em = digest.compose_city_email(conn, "Nashville", as_of=AS_OF, week_index=1)
    assert em["subject"] == "This week's cheapest trips from Nashville"


def test_send_digest_dry_run_composes_per_city_and_skips_unknown(conn):
    conn.execute("INSERT INTO signups (email, created_at, digest_city, unsub_token) "
                 "VALUES ('s@x.com','2026-06-01','Nashville','tok1')")
    conn.execute("INSERT INTO signups (email, created_at, digest_city, unsub_token) "
                 "VALUES ('u@x.com','2026-06-01','Atlantis','tok2')")  # not a served city
    conn.commit()
    summary = digest.send_digest(conn, as_of=AS_OF, dry_run=True)
    assert summary["subscribers"] == 2
    assert summary["would_send"] == 1
    assert summary["skipped_no_content"] == 1
    assert summary["by_city"] == {"Nashville": 1}


# ---------- subscription / db pipeline ----------

@pytest.fixture
def dbenv(temp_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    init_schema(temp_db_path)
    return temp_db_path


def test_insert_signup_sets_digest_city_and_token(dbenv):
    db.insert_signup("a@x.com", digest_city="Nashville")
    row = db.get_signup_by_email("a@x.com")
    assert row["digest_city"] == "Nashville"
    assert row["unsub_token"]


def test_insert_signup_backfills_city_on_repeat(dbenv):
    db.insert_signup("b@x.com")                       # homepage, no city
    db.insert_signup("b@x.com", digest_city="Miami")  # later hub signup supplies it
    assert db.get_signup_by_email("b@x.com")["digest_city"] == "Miami"


def test_get_digest_subscribers_excludes_cityless_and_unsubscribed(dbenv):
    db.insert_signup("city@x.com", digest_city="Nashville")
    db.insert_signup("nocity@x.com")
    db.insert_signup("gone@x.com", digest_city="Miami")
    db.unsubscribe_by_token(db.get_signup_by_email("gone@x.com")["unsub_token"])
    assert [r["email"] for r in db.get_digest_subscribers()] == ["city@x.com"]


def test_unsubscribe_by_token_is_idempotent_and_rejects_unknown(dbenv):
    db.insert_signup("u@x.com", digest_city="Boston")
    tok = db.get_signup_by_email("u@x.com")["unsub_token"]
    assert db.unsubscribe_by_token(tok) is True
    assert db.unsubscribe_by_token(tok) is True       # already-unsubscribed still ok
    assert db.unsubscribe_by_token("bogus") is False
    assert db.get_signup_by_email("u@x.com")["unsubscribed_at"] is not None


def test_signup_api_sets_digest_city(client, temp_db_path):
    with patch("server.email_client.send_confirmation", return_value={"id": "m"}):
        client.post("/api/signup", json={"email": "hub@x.com", "hub_city": "Denver"},
                    headers={"Accept": "application/json"})
    c = sqlite3.connect(temp_db_path)
    row = c.execute("SELECT digest_city, unsub_token FROM signups WHERE email='hub@x.com'").fetchone()
    c.close()
    assert row[0] == "Denver" and row[1]


def test_unsubscribe_route(client, temp_db_path):
    with patch("server.email_client.send_confirmation", return_value={"id": "m"}):
        client.post("/api/signup", json={"email": "un@x.com", "hub_city": "Boston"},
                    headers={"Accept": "application/json"})
    c = sqlite3.connect(temp_db_path)
    tok = c.execute("SELECT unsub_token FROM signups WHERE email='un@x.com'").fetchone()[0]
    c.close()
    resp = client.get(f"/unsubscribe?token={tok}")
    assert resp.status_code == 200
    assert b"unsubscribed" in resp.data.lower()
    c = sqlite3.connect(temp_db_path)
    assert c.execute("SELECT unsubscribed_at FROM signups WHERE email='un@x.com'").fetchone()[0] is not None
    c.close()
    assert client.get("/unsubscribe?token=bogus").status_code == 404
