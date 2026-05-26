"""Integration tests for POST /api/go."""
import sqlite3

import pytest


@pytest.fixture
def seeded_client(client, temp_db_path):
    """Client with airports + 3 destinations + price snapshots seeded."""
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('BNA','Nashville','TN','Southeast',36.1,-86.7,12)")
        conn.execute("INSERT INTO destinations VALUES ('MEX','Mexico City','Mexico','MX','LA','[\"city\",\"food\"]',1,0,'[3,4,5,10,11]',60,2,'MXN',19.4,-99.1,'It is a city, not a beach.',3)")
        conn.execute("INSERT INTO destinations VALUES ('LIS','Lisbon','Portugal','PT','WE','[\"city\",\"food\",\"history\"]',1,0,'[5,6,9]',80,1,'EUR',38.7,-9.1,'February rains 18 of 28 days.',4)")
        conn.execute("INSERT INTO destinations VALUES ('SJU','San Juan','Puerto Rico','PR','LA','[\"beach\"]',0,0,'[12,1,2,3]',90,2,'USD',18.4,-66.1,'No passport needed.',2)")
        conn.execute("INSERT INTO routes VALUES ('BNA','MEX','Routes via DFW.')")
        conn.execute("INSERT INTO routes VALUES ('BNA','LIS',NULL)")
        conn.execute("INSERT INTO routes VALUES ('BNA','SJU',NULL)")
        for o, d, dep, ret, n, p in [
            ('BNA','MEX','2026-06-01','2026-06-08',7,342),
            ('BNA','LIS','2026-06-15','2026-06-22',7,612),
            ('BNA','SJU','2026-06-05','2026-06-12',7,298),
        ]:
            conn.execute(
                "INSERT INTO price_snapshots (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,stops,carrier_codes,source,fetched_at) VALUES (?,?,?,?,?,?,NULL,NULL,'fli','2026-05-26T07:00')",
                (o, d, dep, ret, n, p)
            )
        conn.commit()
    finally:
        conn.close()
    return client


def test_api_go_returns_candidates_within_budget(seeded_client):
    rv = seeded_client.post("/api/go", json={
        "origin_iata": "BNA",
        "budget_usd": 500,
        "trip_nights": 7,
        "vibes": [],
    })
    assert rv.status_code == 200
    body = rv.get_json()
    iatas = [c["iata"] for c in body["results"]]
    assert "MEX" in iatas
    assert "SJU" in iatas
    assert "LIS" not in iatas


def test_api_go_returns_card_fields(seeded_client):
    rv = seeded_client.post("/api/go", json={
        "origin_iata": "BNA",
        "budget_usd": 500,
        "trip_nights": 7,
        "vibes": [],
    })
    body = rv.get_json()
    card = next(c for c in body["results"] if c["iata"] == "MEX")
    assert card["city"] == "Mexico City"
    assert card["country"] == "Mexico"
    assert card["price_usd"] == 342
    assert "departure_date" in card
    assert card["catch"] == "It is a city, not a beach. Routes via DFW."
    assert "google_flights_url" in card


def test_api_go_filters_by_vibe(seeded_client):
    rv = seeded_client.post("/api/go", json={
        "origin_iata": "BNA",
        "budget_usd": 500,
        "trip_nights": 7,
        "vibes": ["beach"],
    })
    body = rv.get_json()
    iatas = [c["iata"] for c in body["results"]]
    assert "SJU" in iatas
    assert "MEX" not in iatas


def test_api_go_sets_session_cookie(seeded_client):
    rv = seeded_client.post("/api/go", json={
        "origin_iata": "BNA", "budget_usd": 500, "trip_nights": 7, "vibes": [],
    })
    cookies = rv.headers.getlist("Set-Cookie")
    assert any("promptiv_session=" in c for c in cookies)


def test_api_go_validates_required_fields(seeded_client):
    rv = seeded_client.post("/api/go", json={"budget_usd": 500})
    assert rv.status_code == 400


def test_api_go_clamps_trip_nights_to_valid_values(seeded_client):
    """trip_nights must be 5, 7, or 10 (the cached values)."""
    rv = seeded_client.post("/api/go", json={
        "origin_iata": "BNA", "budget_usd": 500, "trip_nights": 12, "vibes": [],
    })
    assert rv.status_code == 400
