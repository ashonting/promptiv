import sqlite3
import pytest
from server.migrations import init_schema
from server import watch_emails


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    # curated destination for all-in enrichment
    c.execute("INSERT INTO destinations (iata, city, country, country_code, region, vibes, passport_required, visa_required_us, best_months, avg_daily_cost_usd, safety_tier, currency, lat, lng, base_catch, novelty_score) VALUES ('PLS','Providenciales','Turks and Caicos','TC','Caribbean','[\"beach\"]',1,0,'[12]',250,1,'USD',21.7,-72.2,NULL,3)")
    c.commit()
    yield c
    c.close()


WATCH = {"id": 1, "email": "a@b.co", "origin_iata": "BNA", "dest_iata": "PLS",
         "window_start": "2026-11-01", "window_end": "2027-01-31",
         "trip_nights": 7, "ceiling_usd": None, "manage_token": "tok123"}

DECISION = {"trigger": "drop", "override": False, "nights_watched": 47,
            "percentile": 8.0, "trailing_low": 410}


def test_alert_subject_and_receipts(conn):
    msg = watch_emails.compose_alert(
        conn, WATCH, DECISION, best=(325, "2026-12-09", "2026-12-16"),
        base_url="https://dashaway.io")
    assert msg["subject"].startswith("↓ $325")
    assert "Turks" in msg["subject"] or "Providenciales" in msg["subject"]
    assert "47 nights" in msg["html"]
    assert "Dec 9" in msg["html"]
    # all-in enrichment: 325 + 7*250 = 2075
    assert "2,075" in msg["html"]
    # google flights deep link + manage link present
    assert "google.com/travel/flights" in msg["html"]
    assert "manage?token=tok123" in msg["html"]
    assert "verify" in msg["text"].lower()


def test_alert_without_catalog_dest_skips_allin(conn):
    w = dict(WATCH, dest_iata="GRR")
    msg = watch_emails.compose_alert(conn, w, DECISION,
                                     best=(86, "2026-12-09", "2026-12-16"),
                                     base_url="https://dashaway.io")
    assert "all-in" not in msg["html"].lower()


def test_percentile_receipt_only_when_available(conn):
    d = dict(DECISION, percentile=None, nights_watched=3)
    msg = watch_emails.compose_alert(conn, WATCH, d,
                                     best=(325, "2026-12-09", "2026-12-16"),
                                     base_url="https://dashaway.io")
    assert "bottom" not in msg["html"].lower()


def test_pulse_lists_watches(conn):
    rows = [dict(WATCH, _best=(389, "2026-12-09", "2026-12-16"),
                 _nights=47, _trend="down")]
    msg = watch_emails.compose_pulse(rows, base_url="https://dashaway.io")
    assert "389" in msg["html"] and "47 nights" in msg["html"]
    assert "manage?token=tok123" in msg["html"]


def test_confirm_email_has_link_and_details(conn):
    from unittest.mock import patch
    with patch("server.email_client.send_digest_email", return_value={"id": "m"}) as send:
        watch_emails.send_watch_confirm(
            "a@b.co", WATCH, "https://dashaway.io/watch/confirm?token=tok123")
    args = send.call_args[0]
    assert args[0] == "a@b.co"
    assert "confirm" in args[1].lower()
    assert "confirm?token=tok123" in args[2]
    assert "BNA" in args[2] and "PLS" in args[2]
