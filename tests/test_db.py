"""Tests for db access layer."""
import pytest
from server.migrations import init_schema
from server import db


@pytest.fixture
def initialized_db(temp_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    init_schema(temp_db_path)
    return temp_db_path


def test_insert_signup_returns_id(initialized_db):
    signup_id = db.insert_signup("a@example.com", ip_hash="abc", referrer="https://x.com")
    assert signup_id is not None
    assert signup_id >= 1


def test_insert_signup_dedup_returns_existing_id(initialized_db):
    first_id = db.insert_signup("a@example.com", ip_hash="abc")
    second_id = db.insert_signup("a@example.com", ip_hash="def")
    assert first_id == second_id


def test_get_signup_by_email_returns_row(initialized_db):
    db.insert_signup("a@example.com", ip_hash="abc")
    row = db.get_signup_by_email("a@example.com")
    assert row is not None
    assert row["email"] == "a@example.com"


def test_get_signup_by_email_missing_returns_none(initialized_db):
    assert db.get_signup_by_email("nobody@example.com") is None


def test_upsert_qualifiers_creates_row(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    db.upsert_qualifiers(signup_id, budget_bucket="mid", home_airport="BNA", frustration="too many tabs")
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "mid"
    assert row["home_airport"] == "BNA"
    assert row["frustration"] == "too many tabs"


def test_upsert_qualifiers_updates_existing(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    db.upsert_qualifiers(signup_id, budget_bucket="low")
    db.upsert_qualifiers(signup_id, budget_bucket="stretch", home_airport="LAX")
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "stretch"
    assert row["home_airport"] == "LAX"


def test_upsert_qualifiers_rejects_bad_bucket(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    with pytest.raises(ValueError):
        db.upsert_qualifiers(signup_id, budget_bucket="invalid")


def test_count_signups(initialized_db):
    assert db.count_signups() == 0
    db.insert_signup("a@example.com")
    db.insert_signup("b@example.com")
    assert db.count_signups() == 2


def test_find_candidates_filters_by_origin_and_budget(temp_db_path, monkeypatch):
    """find_candidates returns destinations within budget, joined with cheapest price."""
    import sqlite3
    from server.migrations import init_schema
    from server.db import find_candidates

    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('BNA','Nashville','TN','Southeast',36.1,-86.7,12)")
        conn.execute("INSERT INTO destinations VALUES ('MEX','Mexico City','Mexico','MX','LA','[\"city\"]',1,0,'[3,4,5]',60,2,'MXN',19.4,-99.1,'catch1',3)")
        conn.execute("INSERT INTO destinations VALUES ('LIS','Lisbon','Portugal','PT','WE','[\"city\",\"food\"]',1,0,'[5,6]',80,1,'EUR',38.7,-9.1,'catch2',4)")
        conn.execute("INSERT INTO routes VALUES ('BNA','MEX','via DFW')")
        conn.execute("INSERT INTO routes VALUES ('BNA','LIS',NULL)")
        conn.execute("INSERT INTO price_snapshots (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,stops,carrier_codes,source,fetched_at) VALUES ('BNA','MEX','2026-06-01','2026-06-08',7,342,0,'[\"AA\"]','fli','2026-05-26T07:00')")
        conn.execute("INSERT INTO price_snapshots (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,stops,carrier_codes,source,fetched_at) VALUES ('BNA','LIS','2026-06-15','2026-06-22',7,612,1,'[\"BA\"]','fli','2026-05-26T07:00')")
        conn.commit()

        cands = find_candidates(conn, origin_iata="BNA", budget_usd=500, trip_nights=7)
    finally:
        conn.close()

    iatas = [c["iata"] for c in cands]
    assert "MEX" in iatas
    assert "LIS" not in iatas  # $612 over $500 + 15% = $575


def test_find_candidates_returns_cheapest_price_per_destination(temp_db_path):
    """Multiple snapshots for same route → returns the cheapest."""
    import sqlite3
    from server.migrations import init_schema
    from server.db import find_candidates

    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('BNA','Nashville','TN','Southeast',36.1,-86.7,12)")
        conn.execute("INSERT INTO destinations VALUES ('MEX','Mexico City','Mexico','MX','LA','[]',1,0,'[]',60,2,'MXN',19.4,-99.1,NULL,3)")
        conn.execute("INSERT INTO routes VALUES ('BNA','MEX',NULL)")
        for price, dep in [(450, '2026-06-01'), (342, '2026-06-08'), (399, '2026-06-15')]:
            conn.execute("INSERT INTO price_snapshots (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,stops,carrier_codes,source,fetched_at) VALUES (?,?,?,?,?,?,0,'[]','fli','2026-05-26T07:00')",
                         ('BNA','MEX',dep,'2026-06-08',7,price))
        conn.commit()
        cands = find_candidates(conn, origin_iata="BNA", budget_usd=500, trip_nights=7)
    finally:
        conn.close()

    assert len(cands) == 1
    assert cands[0]["price_usd"] == 342


def test_record_search_persists(temp_db_path):
    import json, sqlite3
    from server.migrations import init_schema
    from server.db import record_search, count_searches

    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        record_search(
            conn,
            session_id="sess123",
            origin_iata="BNA",
            budget_usd=500,
            trip_nights=7,
            vibe_filter=["city", "food"],
            result_iatas=["MEX", "LIS"],
        )
        conn.commit()
        assert count_searches(conn, "sess123") == 1
        row = conn.execute("SELECT vibe_filter, result_iatas FROM searches WHERE session_id=?", ("sess123",)).fetchone()
    finally:
        conn.close()
    assert json.loads(row[0]) == ["city", "food"]
    assert json.loads(row[1]) == ["MEX", "LIS"]
