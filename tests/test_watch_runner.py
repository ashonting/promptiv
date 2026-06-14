from datetime import date
import sqlite3
from unittest.mock import patch
import pytest
from server.migrations import init_schema
from server import watches, watch_runner


class FakeResult:
    def __init__(self, dep, ret, price, origin="BNA", dest="PLS"):
        self.origin_iata = origin; self.dest_iata = dest
        self.departure_date = dep; self.return_date = ret
        self.trip_nights = 7; self.total_price_usd = price
        self.stops = 0; self.carrier_codes = ["G4"]


class FakeFli:
    def __init__(self, results=None, raises=None):
        self.results = results or []
        self.raises = raises
        self.calls = []

    def search_dates(self, origin, dest, start_date, end_date, trip_nights):
        self.calls.append((origin, dest, start_date, end_date, trip_nights))
        if self.raises:
            raise self.raises
        return self.results


@pytest.fixture
def conn(temp_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    monkeypatch.setenv("OPS_EMAIL", "ops@example.com")
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _watch(conn, email="a@b.co", dest="PLS"):
    w = watches.create_watch(conn, email=email, origin="BNA", dest=dest,
                             window_start="2026-11-01", window_end="2027-01-31",
                             trip_nights=7, today=date(2026, 6, 10))
    watches.confirm_watch(conn, w["manage_token"])
    return w


def test_scan_writes_watch_observations(conn):
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325),
                   FakeResult("2026-11-04", "2026-11-11", 460)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert len(fli.calls) == 1
    rows = dict(conn.execute(
        "SELECT source, COUNT(*) FROM fare_observations GROUP BY source").fetchall())
    assert rows["watch"] == 2
    assert summary["scanned"] == 1 and summary["errors"] == 0


def test_dedupe_same_route_window(conn):
    _watch(conn, email="a@b.co")
    _watch(conn, email="b@c.co")          # same route+window+nights
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        watch_runner.run(conn, fli=fli, sleep_s=0, today=date(2026, 6, 10),
                         base_url="http://x")
    assert len(fli.calls) == 1            # one request serves both watches


def test_alert_sent_and_logged_on_trigger(conn):
    _watch(conn)
    # seed a prior night at 500 so tonight's 325 is a >=12% drop
    conn.execute("INSERT INTO fare_observations (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,source,observed_date,fetched_at) VALUES ('BNA','PLS','2026-12-09','2026-12-16',7,500,'watch','2026-06-09','x')")
    conn.commit()
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["alerts"] == 1
    assert send.call_count >= 1
    ev = conn.execute("SELECT kind, trigger, best_price FROM watch_events").fetchone()
    assert ev["kind"] == "alert" and ev["trigger"] == "drop" and ev["best_price"] == 325
    assert conn.execute("SELECT last_alert_at FROM watches").fetchone()[0] is not None


def test_plausibility_guard_filters_garbage(conn):
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 7000),   # implausible
                   FakeResult("2026-12-10", "2026-12-17", 410)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        watch_runner.run(conn, fli=fli, sleep_s=0, today=date(2026, 6, 10),
                         base_url="http://x")
    prices = [r[0] for r in conn.execute(
        "SELECT total_price_usd FROM fare_observations WHERE source='watch'")]
    assert prices == [410]


def test_429_aborts_night(conn):
    _watch(conn, email="a@b.co", dest="PLS")
    _watch(conn, email="b@c.co", dest="GRR")
    fli = FakeFli(raises=RuntimeError("HTTP 429 rate-limited"))
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["aborted_429"] is True
    assert len(fli.calls) == 1            # stopped immediately, no second route
    assert send.call_count == 1           # the ops alert email only


def test_non_429_error_skips_route_and_continues(conn):
    _watch(conn, email="a@b.co", dest="PLS")
    _watch(conn, email="b@c.co", dest="GRR")
    calls = {"n": 0}

    class Flaky(FakeFli):
        def search_dates(self, origin, dest, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return [FakeResult("2026-12-09", "2026-12-16", 325,
                               origin=origin, dest=dest)]

    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=Flaky(), sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["errors"] == 1 and summary["scanned"] == 2


def test_summary_reports_observations_written(conn):
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325),
                   FakeResult("2026-11-04", "2026-11-11", 460)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["obs_written"] == 2
    assert summary["empty_routes"] == 0


def test_all_empty_routes_is_a_tripwire(conn):
    _watch(conn)
    fli = FakeFli([])                      # Google returns an empty grid
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["obs_written"] == 0
    assert summary["empty_routes"] == 1
    subject = send.call_args[0][1]
    assert "tripwire" in subject.lower()
    assert "empty" in subject.lower()


def test_error_routes_do_not_count_as_empty(conn):
    _watch(conn)
    fli = FakeFli(raises=RuntimeError("boom"))
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["errors"] == 1
    assert summary["empty_routes"] == 0


def test_clamps_past_window_start_to_tomorrow(conn):
    # window 11-01..01-31; "today" is 11-15 so window_start is in the PAST
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 11, 15), base_url="http://x")
    # fli must be asked to start from tomorrow (11-16), never the stale 11-01
    assert fli.calls[0][2] == date(2026, 11, 16)
    assert summary["errors"] == 0 and summary["obs_written"] == 1


def test_fully_past_window_expires_watch(conn):
    w = _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2027, 2, 15), base_url="http://x")
    assert len(fli.calls) == 0            # nothing left to search
    assert summary["expired"] == 1 and summary["errors"] == 0
    assert conn.execute("SELECT status FROM watches WHERE id=?",
                        (w["id"],)).fetchone()[0] == "expired"
