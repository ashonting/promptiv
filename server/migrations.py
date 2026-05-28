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

CREATE TABLE IF NOT EXISTS airports (
    iata        TEXT PRIMARY KEY,
    city        TEXT NOT NULL,
    state       TEXT,
    region_us   TEXT NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    rank_us     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS destinations (
    iata                TEXT PRIMARY KEY,
    city                TEXT NOT NULL,
    country             TEXT NOT NULL,
    country_code        TEXT NOT NULL,
    region              TEXT NOT NULL,
    vibes               TEXT NOT NULL,
    passport_required   INTEGER NOT NULL,
    visa_required_us    INTEGER NOT NULL,
    best_months         TEXT NOT NULL,
    avg_daily_cost_usd  INTEGER NOT NULL,
    safety_tier         INTEGER NOT NULL,
    currency            TEXT NOT NULL,
    lat                 REAL NOT NULL,
    lng                 REAL NOT NULL,
    base_catch          TEXT,
    novelty_score       INTEGER NOT NULL,
    UNIQUE(city, country)
);

CREATE TABLE IF NOT EXISTS routes (
    origin_iata      TEXT NOT NULL REFERENCES airports(iata),
    dest_iata        TEXT NOT NULL REFERENCES destinations(iata),
    route_catch_text TEXT,
    PRIMARY KEY (origin_iata, dest_iata)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_iata       TEXT NOT NULL REFERENCES airports(iata),
    dest_iata         TEXT NOT NULL REFERENCES destinations(iata),
    departure_date    TEXT NOT NULL,
    return_date       TEXT NOT NULL,
    trip_nights       INTEGER NOT NULL,
    total_price_usd   INTEGER NOT NULL,
    stops             INTEGER,
    carrier_codes     TEXT,
    source            TEXT NOT NULL,
    fetched_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS searches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    origin_iata   TEXT NOT NULL,
    budget_usd    INTEGER NOT NULL,
    trip_nights   INTEGER NOT NULL,
    vibe_filter   TEXT,
    result_iatas  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_iata         TEXT NOT NULL,
    dest_iata           TEXT NOT NULL,
    trip_nights         INTEGER NOT NULL,
    cheapest_price_usd  INTEGER NOT NULL,
    observed_date       TEXT NOT NULL,
    source              TEXT NOT NULL DEFAULT 'fli',
    UNIQUE(origin_iata, dest_iata, trip_nights, observed_date, source)
);

CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
CREATE INDEX IF NOT EXISTS idx_qualifiers_signup_id ON qualifiers(signup_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_lookup ON price_snapshots(origin_iata, total_price_usd, trip_nights, departure_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_dest ON price_snapshots(dest_iata, fetched_at);
CREATE INDEX IF NOT EXISTS idx_searches_session ON searches(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_price_history_route ON price_history(origin_iata, dest_iata, trip_nights, observed_date);
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
