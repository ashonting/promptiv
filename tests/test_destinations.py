"""Tests for the YAML-to-DB loader."""
import json
import sqlite3

import pytest

from server.destinations import load_all, populate_missing_routes
from server.migrations import init_schema


@pytest.fixture
def seeded_db(temp_db_path, tmp_path, monkeypatch):
    """Tmp DB initialized + tmp data dir with minimal valid YAML."""
    init_schema(temp_db_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "airports.yaml").write_text("""
- iata: BNA
  city: Nashville
  state: TN
  region_us: Southeast
  lat: 36.1245
  lng: -86.6782
  rank_us: 12
""")
    (data_dir / "destinations.yaml").write_text("""
- iata: CDMX
  city: Mexico City
  country: Mexico
  country_code: MX
  region: Latin America
  vibes: [city, food, history]
  passport_required: true
  visa_required_us: false
  best_months: [3, 4, 5, 10, 11]
  avg_daily_cost_usd: 60
  safety_tier: 2
  currency: MXN
  lat: 19.4326
  lng: -99.1332
  novelty_score: 3
  base_catch: "It's a city, not a beach."
""")
    (data_dir / "routes.yaml").write_text("""
- origin: BNA
  dest: CDMX
  catch: "BNA->CDMX routes via DFW most days."
""")
    return temp_db_path, data_dir


def test_load_all_inserts_airport(seeded_db):
    db_path, data_dir = seeded_db
    load_all(db_path, data_dir)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT iata, city FROM airports").fetchall()
    finally:
        conn.close()
    assert ("BNA", "Nashville") in rows


def test_load_all_inserts_destination(seeded_db):
    db_path, data_dir = seeded_db
    load_all(db_path, data_dir)

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT city, vibes, best_months, passport_required FROM destinations WHERE iata=?",
            ("CDMX",),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "Mexico City"
    assert json.loads(row[1]) == ["city", "food", "history"]
    assert json.loads(row[2]) == [3, 4, 5, 10, 11]
    assert row[3] == 1  # passport_required = true → 1


def test_load_all_inserts_explicit_route(seeded_db):
    db_path, data_dir = seeded_db
    load_all(db_path, data_dir)

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT route_catch_text FROM routes WHERE origin_iata=? AND dest_iata=?",
            ("BNA", "CDMX"),
        ).fetchone()
    finally:
        conn.close()
    assert "BNA->CDMX" in row[0]


def test_load_all_is_idempotent(seeded_db):
    db_path, data_dir = seeded_db
    load_all(db_path, data_dir)
    load_all(db_path, data_dir)  # run twice

    conn = sqlite3.connect(db_path)
    try:
        airports = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
        dests = conn.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
        routes = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    finally:
        conn.close()
    assert airports == 1
    assert dests == 1
    assert routes == 1


def test_populate_missing_routes_creates_null_catch_rows(temp_db_path):
    """For every (airport, dest) pair without a routes.yaml entry, insert a row with null catch."""
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('JFK','NY','NY','NE',40.6,-73.8,1)")
        conn.execute("INSERT INTO airports VALUES ('LAX','LA','CA','W',33.9,-118.4,2)")
        conn.execute(
            "INSERT INTO destinations VALUES ('CDMX','Mexico City','Mexico','MX','LA','[]',1,0,'[]',60,2,'MXN',19.4,-99.1,NULL,3)"
        )
        conn.execute(
            "INSERT INTO destinations VALUES ('TBS','Tbilisi','Georgia','GE','CC','[]',1,0,'[]',35,1,'GEL',41.7,44.8,NULL,5)"
        )
        conn.execute("INSERT INTO routes VALUES ('JFK','CDMX','custom')")
        conn.commit()

        populate_missing_routes(conn)
        conn.commit()

        rows = conn.execute("SELECT origin_iata, dest_iata, route_catch_text FROM routes ORDER BY origin_iata, dest_iata").fetchall()
    finally:
        conn.close()

    assert len(rows) == 4
    by_pair = {(o, d): c for o, d, c in rows}
    assert by_pair[("JFK", "CDMX")] == "custom"
    assert by_pair[("JFK", "TBS")] is None
    assert by_pair[("LAX", "CDMX")] is None
    assert by_pair[("LAX", "TBS")] is None
