"""Tests for the nightly price refresh entry point. Uses mock fli."""
import sqlite3
from datetime import date

import pytest

from server.migrations import init_schema
from server.price_refresh import refresh_route, refresh_all
from server.fli_client import FliClient


@pytest.fixture
def seeded_db(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('BNA','Nashville','TN','SE',36.1,-86.7,12)")
        conn.execute("INSERT INTO destinations VALUES ('MEX','Mexico City','Mexico','MX','LA','[]',1,0,'[]',60,2,'MXN',19.4,-99.1,NULL,3)")
        conn.execute("INSERT INTO routes VALUES ('BNA','MEX',NULL)")
        conn.commit()
    finally:
        conn.close()
    return temp_db_path


def test_refresh_route_inserts_snapshots(seeded_db):
    fli = FliClient(mock=True)
    refresh_route(seeded_db, fli, origin="BNA", dest="MEX", trip_nights=7,
                  start_date=date(2026, 6, 1), end_date=date(2026, 8, 30))

    conn = sqlite3.connect(seeded_db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM price_snapshots WHERE origin_iata='BNA' AND dest_iata='MEX' AND trip_nights=7"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count > 0


def test_refresh_route_clears_old_snapshots_for_same_route(seeded_db):
    """Re-running for the same (origin, dest, nights) replaces older rows."""
    fli = FliClient(mock=True)
    refresh_route(seeded_db, fli, "BNA", "MEX", 7, date(2026, 6, 1), date(2026, 7, 31))
    conn = sqlite3.connect(seeded_db)
    first = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    conn.close()

    refresh_route(seeded_db, fli, "BNA", "MEX", 7, date(2026, 6, 1), date(2026, 7, 31))
    conn = sqlite3.connect(seeded_db)
    second = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    conn.close()
    assert first == second


def test_refresh_all_iterates_all_routes(seeded_db):
    conn = sqlite3.connect(seeded_db)
    conn.execute("INSERT INTO destinations VALUES ('LIS','Lisbon','Portugal','PT','WE','[]',1,0,'[]',80,1,'EUR',38.7,-9.1,NULL,4)")
    conn.execute("INSERT INTO routes VALUES ('BNA','LIS',NULL)")
    conn.commit()
    conn.close()

    fli = FliClient(mock=True)
    summary = refresh_all(seeded_db, fli, trip_lengths=[7], sleep_seconds=0)
    assert summary["routes_attempted"] == 2
    assert summary["snapshots_written"] > 0
