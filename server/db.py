"""SQLite access layer for Promptiv teaser."""
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional


VALID_BUDGET_BUCKETS = {"low", "mid", "stretch"}


def _connect() -> sqlite3.Connection:
    db_path = os.environ.get("DATABASE_PATH")
    if not db_path:
        raise RuntimeError("DATABASE_PATH not set")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_signup(email: str, ip_hash: Optional[str] = None, referrer: Optional[str] = None,
                  digest_city: Optional[str] = None) -> int:
    """Insert a signup (= a weekly-digest subscription). If the email exists,
    return the existing id; backfill its digest_city / unsub_token if missing so a
    later hub signup can supply the city a homepage signup didn't have."""
    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id, digest_city, unsub_token FROM signups WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            eid = int(existing["id"])
            updates = {}
            if digest_city and not existing["digest_city"]:
                updates["digest_city"] = digest_city
            if not existing["unsub_token"]:
                updates["unsub_token"] = secrets.token_urlsafe(24)
            if updates:
                sets = ", ".join(f"{k} = ?" for k in updates)
                conn.execute(f"UPDATE signups SET {sets} WHERE id = ?", (*updates.values(), eid))
                conn.commit()
            return eid

        cur = conn.execute(
            "INSERT INTO signups (email, created_at, ip_hash, referrer, digest_city, unsub_token) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (email, _now(), ip_hash, referrer, digest_city, secrets.token_urlsafe(24)),
        )
        conn.commit()
        new_id = cur.lastrowid
        if new_id is None:
            raise RuntimeError("INSERT succeeded but lastrowid is None")
        return new_id
    finally:
        conn.close()


def get_digest_subscribers() -> list:
    """Active subscribers with a known served city, for the weekly digest."""
    conn = _connect()
    try:
        return conn.execute(
            "SELECT email, digest_city, unsub_token FROM signups "
            "WHERE unsubscribed_at IS NULL AND digest_city IS NOT NULL AND digest_city != '' "
            "ORDER BY digest_city, email"
        ).fetchall()
    finally:
        conn.close()


def unsubscribe_by_token(token: Optional[str]) -> bool:
    """Mark the subscriber with this token unsubscribed. Returns True if the
    token is valid (already-unsubscribed counts as success), False if unknown."""
    if not token:
        return False
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, unsubscribed_at FROM signups WHERE unsub_token = ?", (token,)
        ).fetchone()
        if not row:
            return False
        if row["unsubscribed_at"] is None:
            conn.execute("UPDATE signups SET unsubscribed_at = ? WHERE id = ?", (_now(), row["id"]))
            conn.commit()
        return True
    finally:
        conn.close()


def get_signup_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE email = ?", (email,))
        return cur.fetchone()
    finally:
        conn.close()


def get_signup_by_id(signup_id: int) -> Optional[sqlite3.Row]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def upsert_qualifiers(
    signup_id: int,
    budget_bucket: Optional[str] = None,
    home_airport: Optional[str] = None,
    frustration: Optional[str] = None,
) -> None:
    """Insert or update qualifier row for a signup. Validates budget_bucket."""
    if budget_bucket is not None and budget_bucket not in VALID_BUDGET_BUCKETS:
        raise ValueError(f"budget_bucket must be one of {VALID_BUDGET_BUCKETS}, got {budget_bucket}")

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM qualifiers WHERE signup_id = ?", (signup_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE qualifiers
                   SET budget_bucket = COALESCE(?, budget_bucket),
                       home_airport = COALESCE(?, home_airport),
                       frustration = COALESCE(?, frustration)
                   WHERE signup_id = ?""",
                (budget_bucket, home_airport, frustration, signup_id),
            )
        else:
            conn.execute(
                """INSERT INTO qualifiers
                   (signup_id, budget_bucket, home_airport, frustration, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (signup_id, budget_bucket, home_airport, frustration, _now()),
            )
        conn.commit()
    finally:
        conn.close()


def get_qualifiers_by_signup_id(signup_id: int) -> Optional[sqlite3.Row]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM qualifiers WHERE signup_id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def count_signups() -> int:
    conn = _connect()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM signups").fetchone()[0])
    finally:
        conn.close()


def find_candidates(
    conn: sqlite3.Connection,
    origin_iata: str,
    budget_usd: int,
    trip_nights: int,
) -> list[dict]:
    """Return destinations with cheapest cached price within budget+15%.

    Each dict contains: iata, city, country, vibes (list), best_months (list),
    avg_daily_cost_usd, safety_tier, novelty_score, base_catch,
    route_catch_text, price_usd, departure_date, return_date,
    cheapest_date_in_best_months.

    Caller owns the transaction; this function does not commit.
    """
    max_price = int(budget_usd * 1.15)
    rows = conn.execute(
        """
        WITH cheapest AS (
            SELECT dest_iata,
                   MIN(total_price_usd) AS min_price
            FROM price_snapshots
            WHERE origin_iata = ?
              AND trip_nights = ?
              AND total_price_usd <= ?
            GROUP BY dest_iata
        )
        SELECT d.iata, d.city, d.country, d.vibes, d.best_months,
               d.avg_daily_cost_usd, d.safety_tier, d.novelty_score, d.base_catch,
               r.route_catch_text,
               c.min_price,
               s.departure_date, s.return_date
        FROM cheapest c
        JOIN destinations d ON d.iata = c.dest_iata
        LEFT JOIN routes r ON r.origin_iata = ? AND r.dest_iata = d.iata
        JOIN price_snapshots s ON s.origin_iata = ?
                              AND s.dest_iata = c.dest_iata
                              AND s.trip_nights = ?
                              AND s.total_price_usd = c.min_price
        GROUP BY d.iata
        """,
        (origin_iata, trip_nights, max_price, origin_iata, origin_iata, trip_nights),
    ).fetchall()

    out: list[dict] = []
    for row in rows:
        best_months = json.loads(row[4])
        dep_month = int(row[11].split("-")[1])
        out.append({
            "iata": row[0],
            "city": row[1],
            "country": row[2],
            "vibes": json.loads(row[3]),
            "best_months": best_months,
            "avg_daily_cost_usd": row[5],
            "safety_tier": row[6],
            "novelty_score": row[7],
            "base_catch": row[8],
            "route_catch_text": row[9],
            "price_usd": row[10],
            "departure_date": row[11],
            "return_date": row[12],
            "cheapest_date_in_best_months": dep_month in best_months,
        })
    return out


def record_search(
    conn: sqlite3.Connection,
    session_id: str,
    origin_iata: str,
    budget_usd: int,
    trip_nights: int,
    vibe_filter: list[str],
    result_iatas: list[str],
) -> None:
    """Insert a search row. Caller owns the transaction."""
    conn.execute(
        """INSERT INTO searches
           (session_id, origin_iata, budget_usd, trip_nights, vibe_filter, result_iatas, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, origin_iata, budget_usd, trip_nights,
            json.dumps(vibe_filter) if vibe_filter else None,
            json.dumps(result_iatas),
            _now(),
        ),
    )


def count_searches(conn: sqlite3.Connection, session_id: str) -> int:
    """Return count of searches for a session. Returns 0 if none."""
    row = conn.execute(
        "SELECT COUNT(*) FROM searches WHERE session_id = ?", (session_id,)
    ).fetchone()
    return int(row[0])


def session_seen_counts(conn: sqlite3.Connection, session_id: str) -> dict[str, int]:
    """Return {dest_iata: times_appeared} across this session's prior result lists."""
    counts: dict[str, int] = {}
    for (raw,) in conn.execute(
        "SELECT result_iatas FROM searches WHERE session_id = ?", (session_id,)
    ):
        for iata in json.loads(raw):
            counts[iata] = counts.get(iata, 0) + 1
    return counts
