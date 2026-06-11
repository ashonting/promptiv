from datetime import date
import sqlite3
import pytest
from server.migrations import init_schema
from server import watches

TODAY = date(2026, 6, 10)


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _mk(conn, **kw):
    args = dict(email="a@b.co", origin="BNA", dest="PLS",
                window_start="2026-11-01", window_end="2027-01-31",
                trip_nights=7, ceiling_usd=450, ip_hash="h", today=TODAY)
    args.update(kw)
    return watches.create_watch(conn, **args)


def test_create_returns_token_and_pending(conn):
    w = _mk(conn)
    assert len(w["manage_token"]) >= 24
    row = conn.execute("SELECT * FROM watches WHERE id=?", (w["id"],)).fetchone()
    assert row["status"] == "pending"
    assert row["origin_iata"] == "BNA" and row["dest_iata"] == "PLS"


def test_validation_rules(conn):
    with pytest.raises(ValueError, match="airport"):
        _mk(conn, origin="QQQ")
    with pytest.raises(ValueError, match="airport"):
        _mk(conn, dest="qzx")    # 3 letters, lowercase ok, but not a real airport
    with pytest.raises(ValueError, match="origin"):
        _mk(conn, dest="BNA")                       # origin == dest
    with pytest.raises(ValueError, match="nights"):
        _mk(conn, trip_nights=2)
    with pytest.raises(ValueError, match="nights"):
        _mk(conn, trip_nights=15)
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_start="2026-06-01")        # not >= tomorrow
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_end="2027-06-01")          # span > 185 days
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_start="2027-04-15", window_end="2027-04-10")
    with pytest.raises(ValueError, match="email"):
        _mk(conn, email="not-an-email")


def test_one_active_watch_per_email(conn):
    _mk(conn)
    with pytest.raises(ValueError, match="one watch"):
        _mk(conn, dest="GRR")
    # a deleted watch frees the slot
    conn.execute("UPDATE watches SET status='deleted'")
    _mk(conn, dest="GRR")


def test_confirm_flow(conn):
    w = _mk(conn)
    assert watches.confirm_watch(conn, w["manage_token"]) is True
    row = conn.execute("SELECT status, confirmed_at FROM watches").fetchone()
    assert row["status"] == "active" and row["confirmed_at"]
    assert watches.confirm_watch(conn, "nope") is False


def test_manage_actions(conn):
    w = _mk(conn)
    watches.confirm_watch(conn, w["manage_token"])
    assert watches.set_status(conn, w["manage_token"], "paused") is True
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "paused"
    assert watches.set_status(conn, w["manage_token"], "active") is True
    assert watches.set_status(conn, w["manage_token"], "deleted") is True
    assert watches.set_status(conn, "nope", "paused") is False
    with pytest.raises(ValueError):
        watches.set_status(conn, w["manage_token"], "exploded")


def test_ip_rate_limit(conn):
    for i in range(5):
        w = _mk(conn, email=f"u{i}@x.co")
        conn.execute("UPDATE watches SET status='deleted' WHERE id=?", (w["id"],))
    with pytest.raises(ValueError, match="too many"):
        _mk(conn, email="u9@x.co")


def test_active_watches_listing(conn):
    w = _mk(conn)
    assert watches.active_watches(conn) == []          # pending isn't active
    watches.confirm_watch(conn, w["manage_token"])
    acts = watches.active_watches(conn)
    assert len(acts) == 1 and acts[0]["origin_iata"] == "BNA"
