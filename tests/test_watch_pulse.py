from datetime import date
import sqlite3
from unittest.mock import patch
import pytest
from server.migrations import init_schema
from server import watches, watch_pulse


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _seed(conn, email="a@b.co"):
    w = watches.create_watch(conn, email=email, origin="BNA", dest="PLS",
                             window_start="2026-11-01", window_end="2027-01-31",
                             trip_nights=7, today=date(2026, 6, 10))
    watches.confirm_watch(conn, w["manage_token"])
    for day, price in (("2026-06-08", 500), ("2026-06-09", 460)):
        conn.execute("INSERT INTO fare_observations (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,source,observed_date,fetched_at) VALUES ('BNA','PLS','2026-12-09','2026-12-16',7,?,'watch',?,'x')", (price, day))
    conn.commit()
    return w


def test_pulse_sends_one_email_per_user(conn):
    _seed(conn, "a@b.co")
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        n = watch_pulse.send_pulses(conn, base_url="http://x",
                                    today=date(2026, 6, 10), sleep=0)
    assert n == 1 and send.call_count == 1
    args = send.call_args[0]
    assert args[0] == "a@b.co"
    assert "pulse" in args[1].lower()
    ev = conn.execute(
        "SELECT COUNT(*) FROM watch_events WHERE kind='pulse'").fetchone()[0]
    assert ev == 1


def test_pulse_idempotent_same_day(conn):
    _seed(conn)
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        watch_pulse.send_pulses(conn, base_url="http://x",
                                today=date(2026, 6, 10), sleep=0)
        n2 = watch_pulse.send_pulses(conn, base_url="http://x",
                                     today=date(2026, 6, 10), sleep=0)
    assert n2 == 0 and send.call_count == 1


def test_pulse_skips_paused(conn):
    w = _seed(conn)
    watches.set_status(conn, w["manage_token"], "paused")
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        n = watch_pulse.send_pulses(conn, base_url="http://x",
                                    today=date(2026, 6, 10), sleep=0)
    assert n == 0 and send.call_count == 0


def test_pulse_includes_history_receipts(conn):
    _seed(conn)
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        watch_pulse.send_pulses(conn, base_url="http://x",
                                today=date(2026, 6, 10), sleep=0)
    html = send.call_args[0][2]
    assert "2 nights" in html          # two seeded observation nights
    assert "460" in html               # latest best
