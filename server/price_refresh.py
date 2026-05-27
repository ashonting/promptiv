"""Nightly fli price refresh. Run via systemd timer.

Invocation: python -m server.price_refresh
Reads DATABASE_PATH from env. Uses real FliClient unless FLI_MOCK=1.
"""
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from server.fli_client import FliClient, FliError


log = logging.getLogger("price_refresh")


SLEEP_BETWEEN_CALLS = 6.0
WINDOW_DAYS = 90
TRIP_LENGTHS = (5, 7, 10)


def refresh_route(
    db_path: str,
    fli: FliClient,
    origin: str,
    dest: str,
    trip_nights: int,
    start_date: date,
    end_date: date,
) -> int:
    """Refresh one (origin, dest, nights) tuple. Returns rows inserted."""
    results = fli.search_dates(origin, dest, start_date, end_date, trip_nights)
    if not results:
        return 0

    fetched_at = _iso_now()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(
            "DELETE FROM price_snapshots WHERE origin_iata=? AND dest_iata=? AND trip_nights=?",
            (origin, dest, trip_nights),
        )
        inserted = 0
        for r in results:
            conn.execute(
                """INSERT INTO price_snapshots
                   (origin_iata, dest_iata, departure_date, return_date,
                    trip_nights, total_price_usd, stops, carrier_codes,
                    source, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.origin_iata, r.dest_iata,
                    r.departure_date, r.return_date,
                    r.trip_nights, r.total_price_usd,
                    r.stops, json.dumps(r.carrier_codes) if r.carrier_codes else None,
                    "fli", fetched_at,
                ),
            )
            inserted += 1
        conn.commit()
        return inserted
    finally:
        conn.close()


def refresh_all(
    db_path: str,
    fli: FliClient,
    trip_lengths: Iterable[int] = TRIP_LENGTHS,
    sleep_seconds: float = SLEEP_BETWEEN_CALLS,
) -> dict:
    """Iterate every route x trip_length. Returns summary metrics."""
    conn = sqlite3.connect(db_path)
    try:
        pairs = conn.execute(
            "SELECT origin_iata, dest_iata FROM routes ORDER BY origin_iata, dest_iata"
        ).fetchall()
    finally:
        conn.close()

    today = date.today()
    end = today + timedelta(days=WINDOW_DAYS)

    summary = {
        "routes_attempted": 0,
        "routes_succeeded": 0,
        "routes_failed": 0,
        "snapshots_written": 0,
    }

    for origin, dest in pairs:
        for nights in trip_lengths:
            summary["routes_attempted"] += 1
            try:
                n = refresh_route(db_path, fli, origin, dest, nights, today, end)
                summary["snapshots_written"] += n
                summary["routes_succeeded"] += 1
            except FliError as e:
                log.warning("%s->%s %dn failed: %s", origin, dest, nights, e)
                summary["routes_failed"] += 1
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    log.info("refresh done: %s", summary)
    return summary


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db_path = os.environ.get("DATABASE_PATH", "/var/lib/promptiv/teaser.sqlite")
    mock = os.environ.get("FLI_MOCK") == "1"
    fli = FliClient(mock=mock)
    summary = refresh_all(db_path, fli)
    failure_rate = (
        summary["routes_failed"] / summary["routes_attempted"]
        if summary["routes_attempted"] else 0
    )
    if failure_rate > 0.05:
        log.error("FAILURE RATE %.1f%% - investigate", failure_rate * 100)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
