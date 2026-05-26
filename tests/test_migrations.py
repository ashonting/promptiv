"""Tests for schema initialization."""
import sqlite3
from server.migrations import init_schema


def test_init_schema_creates_signups_table(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signups';")
    assert cur.fetchone() is not None
    conn.close()


def test_init_schema_creates_qualifiers_table(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qualifiers';")
    assert cur.fetchone() is not None
    conn.close()


def test_signups_table_has_required_columns(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("PRAGMA table_info(signups);")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "email", "created_at", "ip_hash", "referrer"} <= cols
    conn.close()


def test_qualifiers_table_has_required_columns(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("PRAGMA table_info(qualifiers);")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "signup_id", "budget_bucket", "home_airport", "frustration", "created_at"} <= cols
    conn.close()


def test_init_schema_is_idempotent(temp_db_path):
    init_schema(temp_db_path)
    init_schema(temp_db_path)  # Running twice should not error
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_count = len([r for r in cur.fetchall() if not r[0].startswith("sqlite_")])
    assert table_count >= 2
    conn.close()


def test_email_uniqueness_enforced(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    conn.execute("INSERT INTO signups (email, created_at, ip_hash) VALUES (?, ?, ?)",
                 ("a@example.com", "2026-05-25T00:00:00", "hash1"))
    conn.commit()
    try:
        conn.execute("INSERT INTO signups (email, created_at, ip_hash) VALUES (?, ?, ?)",
                     ("a@example.com", "2026-05-25T00:01:00", "hash2"))
        conn.commit()
        assert False, "Expected IntegrityError on duplicate email"
    except sqlite3.IntegrityError:
        pass
    conn.close()
