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


class _RateLimitOnceClient:
    """Test double: raises rate-limit FliError on first call, then succeeds."""

    def __init__(self, real_client):
        self._real = real_client
        self.calls = 0

    def search_dates(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            from server.fli_client import FliError
            raise FliError("fli call failed for X->Y: Google Flights returned an error response (HTTP 429). The request may be malformed, rate-limited, or blocked.")
        return self._real.search_dates(*args, **kwargs)


class _NonRetryableErrorClient:
    """Test double: raises a non-rate-limit FliError always."""

    def search_dates(self, *args, **kwargs):
        from server.fli_client import FliError
        raise FliError("fli call failed for X->Y: bad gateway 502")


def test_refresh_route_retries_on_rate_limit(seeded_db):
    """A 429 on the first call triggers a single retry that succeeds."""
    fli = _RateLimitOnceClient(FliClient(mock=True))
    refresh_route(
        seeded_db, fli, origin="BNA", dest="MEX", trip_nights=7,
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 30),
        rate_limit_backoff=0,  # don't actually sleep during the test
    )

    assert fli.calls == 2, "expected first call (rate-limited) + retry"
    conn = sqlite3.connect(seeded_db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM price_snapshots WHERE origin_iata='BNA' AND dest_iata='MEX' AND trip_nights=7"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count > 0


def test_refresh_route_does_not_retry_on_non_rate_limit_error(seeded_db):
    """A non-rate-limit error propagates immediately without retry."""
    from server.fli_client import FliError

    fli = _NonRetryableErrorClient()
    with pytest.raises(FliError):
        refresh_route(
            seeded_db, fli, origin="BNA", dest="MEX", trip_nights=7,
            start_date=date(2026, 6, 1), end_date=date(2026, 8, 30),
            rate_limit_backoff=0,
        )
