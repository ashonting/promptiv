import sqlite3
import pytest
from server.migrations import init_schema


def test_watch_tables_exist(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(watches)")}
    assert {"id", "email", "origin_iata", "dest_iata", "window_start",
            "window_end", "trip_nights", "ceiling_usd", "status",
            "manage_token", "ip_hash", "created_at", "confirmed_at",
            "last_alert_at"} <= cols
    ev = {r[1] for r in conn.execute("PRAGMA table_info(watch_events)")}
    assert {"id", "watch_id", "kind", "sent_at", "best_price",
            "best_depart", "best_return", "trigger"} <= ev


def test_manage_token_unique(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    conn.execute("INSERT INTO watches (email, origin_iata, dest_iata, window_start, window_end, trip_nights, status, manage_token, created_at) VALUES ('a@b.c','BNA','PLS','2026-11-01','2027-01-31',7,'pending','tok1','2026-06-10')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO watches (email, origin_iata, dest_iata, window_start, window_end, trip_nights, status, manage_token, created_at) VALUES ('x@y.z','BNA','GRR','2026-11-01','2027-01-31',7,'pending','tok1','2026-06-10')")
