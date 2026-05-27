"""Tests for the session-based email gate counter."""
import sqlite3


def test_count_searches_per_session(temp_db_path):
    from server.migrations import init_schema
    from server.db import record_search, count_searches

    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        for _ in range(5):
            record_search(conn, "sess_A", "BNA", 500, 7, [], ["MEX"])
        for _ in range(2):
            record_search(conn, "sess_B", "JFK", 700, 10, [], ["LIS"])
        conn.commit()
        assert count_searches(conn, "sess_A") == 5
        assert count_searches(conn, "sess_B") == 2
        assert count_searches(conn, "sess_X") == 0
    finally:
        conn.close()


def test_api_go_increments_session_search_count(seeded_client_for_gate, temp_db_path):
    """Each /api/go call writes a searches row tied to the session cookie."""
    from server.db import count_searches

    seeded_client_for_gate.post("/api/go", json={
        "origin_iata": "BNA", "budget_usd": 500, "trip_nights": 7, "vibes": [],
    })
    seeded_client_for_gate.post("/api/go", json={
        "origin_iata": "BNA", "budget_usd": 500, "trip_nights": 7, "vibes": [],
    })
    cookie = seeded_client_for_gate.get_cookie("promptiv_session")
    assert cookie is not None
    conn = sqlite3.connect(temp_db_path)
    try:
        assert count_searches(conn, cookie.value) == 2
    finally:
        conn.close()
