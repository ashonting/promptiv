"""Schema initialization for the DashAway teaser database."""
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

-- Append-only fare archive. Unlike price_snapshots (ephemeral, rewritten each
-- scan for /go) and price_history (one cheapest number per route/day), this
-- keeps the FULL price surface every scan: every departure date's fare, tagged
-- by observed_date. This is the durable time series for booking-curve analysis
-- and date-level deal detection. Never deleted. UNIQUE -> same-day re-runs
-- overwrite rather than duplicate.
CREATE TABLE IF NOT EXISTS fare_observations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_iata       TEXT NOT NULL,
    dest_iata         TEXT NOT NULL,
    departure_date    TEXT NOT NULL,
    return_date       TEXT,
    trip_nights       INTEGER NOT NULL,
    total_price_usd   INTEGER,
    stops             INTEGER,
    carrier_codes     TEXT,
    source            TEXT NOT NULL DEFAULT 'fli',
    observed_date     TEXT NOT NULL,
    fetched_at        TEXT NOT NULL,
    UNIQUE(origin_iata, dest_iata, departure_date, return_date, trip_nights, observed_date, source)
);

-- The pairing engine's durable creative. One curated row per origin: a "cheap"
-- destination and an "anchor" destination, with the headline claim "a week in
-- <cheap> costs less than a week in <anchor>". The pairing (the three IATAs) is
-- hand-curated and stable; the dollar columns + verified flag are FACTS the
-- monitor recomputes on every fare refresh. verified=1 only when the cheap leg's
-- total trip cost is genuinely lower. Nothing unverified is ever served.
CREATE TABLE IF NOT EXISTS city_pairings (
    origin_iata       TEXT PRIMARY KEY,
    cheap_iata        TEXT NOT NULL,
    anchor_iata       TEXT NOT NULL,
    trip_nights       INTEGER NOT NULL DEFAULT 7,
    cheap_total_usd   INTEGER,
    anchor_total_usd  INTEGER,
    margin_usd        INTEGER,
    verified          INTEGER NOT NULL DEFAULT 0,
    last_checked      TEXT
);

CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
CREATE INDEX IF NOT EXISTS idx_qualifiers_signup_id ON qualifiers(signup_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_lookup ON price_snapshots(origin_iata, total_price_usd, trip_nights, departure_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_dest ON price_snapshots(dest_iata, fetched_at);
CREATE INDEX IF NOT EXISTS idx_searches_session ON searches(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_price_history_route ON price_history(origin_iata, dest_iata, trip_nights, observed_date);
CREATE INDEX IF NOT EXISTS idx_fare_obs_route_day ON fare_observations(origin_iata, dest_iata, trip_nights, observed_date);
CREATE INDEX IF NOT EXISTS idx_fare_obs_day ON fare_observations(observed_date);

-- Fare watches: one user-defined route+window watched nightly (Watches v1).
CREATE TABLE IF NOT EXISTS watches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL,
    origin_iata   TEXT NOT NULL,
    dest_iata     TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    trip_nights   INTEGER NOT NULL,
    ceiling_usd   INTEGER,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|active|paused|deleted
    manage_token  TEXT NOT NULL UNIQUE,
    ip_hash       TEXT,
    created_at    TEXT NOT NULL,
    confirmed_at  TEXT,
    last_alert_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_watches_status ON watches(status);
CREATE INDEX IF NOT EXISTS idx_watches_email ON watches(email);

-- Watch event log: powers the 1-alert-per-week covenant + auditing.
CREATE TABLE IF NOT EXISTS watch_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id    INTEGER NOT NULL REFERENCES watches(id),
    kind        TEXT NOT NULL,            -- confirm|alert|pulse
    sent_at     TEXT NOT NULL,
    best_price  INTEGER,
    best_depart TEXT,
    best_return TEXT,
    trigger     TEXT                       -- drop|percentile|ceiling
);
CREATE INDEX IF NOT EXISTS idx_watch_events_watch ON watch_events(watch_id, kind, sent_at);
"""


# Additive column migrations for existing tables (CREATE TABLE IF NOT EXISTS
# can't add columns to a table that already exists). Each entry is applied only
# when the column is missing, so this is idempotent.
#   signups.digest_city     — the served city whose weekly digest they get (W4)
#   signups.unsubscribed_at  — ISO timestamp once they unsubscribe (NULL = active)
#   signups.unsub_token      — opaque token for their one-click unsubscribe link
_COLUMN_MIGRATIONS = [
    ("signups", "digest_city", "TEXT"),
    ("signups", "unsubscribed_at", "TEXT"),
    ("signups", "unsub_token", "TEXT"),
]


def _add_column_if_missing(conn, table: str, column: str, decl: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_schema(db_path: str) -> None:
    """Ensure schema exists at db_path. Idempotent — safe to run repeatedly."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        for table, column, decl in _COLUMN_MIGRATIONS:
            _add_column_if_missing(conn, table, column, decl)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signups_unsub_token ON signups(unsub_token)"
        )
        conn.commit()
    finally:
        conn.close()
