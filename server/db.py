"""SQLite access layer for Promptiv teaser."""
import os
import sqlite3
from datetime import datetime, timezone


VALID_BUDGET_BUCKETS = {"low", "mid", "stretch"}


def _connect():
    db_path = os.environ.get("DATABASE_PATH")
    if not db_path:
        raise RuntimeError("DATABASE_PATH not set")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_signup(email: str, ip_hash: str = None, referrer: str = None) -> int:
    """Insert a signup. If email exists, return the existing row's id (dedup)."""
    conn = _connect()
    try:
        cur = conn.execute("SELECT id FROM signups WHERE email = ?", (email,))
        existing = cur.fetchone()
        if existing:
            return existing["id"]

        cur = conn.execute(
            "INSERT INTO signups (email, created_at, ip_hash, referrer) VALUES (?, ?, ?, ?)",
            (email, _now(), ip_hash, referrer),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_signup_by_email(email: str):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE email = ?", (email,))
        return cur.fetchone()
    finally:
        conn.close()


def get_signup_by_id(signup_id: int):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def upsert_qualifiers(signup_id: int, budget_bucket: str = None,
                      home_airport: str = None, frustration: str = None):
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


def get_qualifiers_by_signup_id(signup_id: int):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM qualifiers WHERE signup_id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def count_signups() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM signups").fetchone()[0]
    finally:
        conn.close()
