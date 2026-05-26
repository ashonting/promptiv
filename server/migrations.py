"""Schema initialization for the Promptiv teaser database."""
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS signups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL,
    ip_hash     TEXT,
    referrer    TEXT
);

CREATE TABLE IF NOT EXISTS qualifiers (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    signup_id              INTEGER NOT NULL REFERENCES signups(id) ON DELETE CASCADE,
    budget_bucket          TEXT CHECK(budget_bucket IN ('low', 'mid', 'stretch')),
    home_airport           TEXT,
    frustration            TEXT,
    created_at             TEXT NOT NULL,
    UNIQUE(signup_id)
);

CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
CREATE INDEX IF NOT EXISTS idx_qualifiers_signup_id ON qualifiers(signup_id);
"""


def init_schema(db_path: str) -> None:
    """Ensure schema exists at db_path. Idempotent — safe to run repeatedly."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
