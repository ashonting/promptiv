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
from server import pairings
from server.email_client import send_pairing_alert


log = logging.getLogger("price_refresh")


SLEEP_BETWEEN_CALLS = 6.0
WINDOW_DAYS = 90
TRIP_LENGTHS = (7,)  # v1: 7-night only to stay under 12h timeout. v1.1: re-add 5 and 10
                     # once we either parallelize, raise timeout, or get less aggressive
                     # rate-limiting from Google.
RATE_LIMIT_BACKOFF_SECONDS = 60.0

# Plausibility band for a cheapest-economy round-trip from a US city. Fares
# outside this are bad scrapes (error/business-class prices, e.g. a $7k Bratislava
# "economy" fare) and are dropped before they pollute the durable archive. The
# real observed range is ~$110-$1,700, so this is generous.
MIN_FARE_USD = 40
MAX_FARE_USD = 3500


def _plausible(price) -> bool:
    return price is not None and MIN_FARE_USD <= price <= MAX_FARE_USD


def _is_rate_limit_error(err: Exception) -> bool:
    """Detect HTTP 429 / rate-limit signals in an FliError message."""
    msg = str(err).lower()
    return "429" in msg or "rate-limit" in msg or "rate limit" in msg


def refresh_route(
    db_path: str,
    fli: FliClient,
    origin: str,
    dest: str,
    trip_nights: int,
    start_date: date,
    end_date: date,
    rate_limit_backoff: float = RATE_LIMIT_BACKOFF_SECONDS,
) -> int:
    """Refresh one (origin, dest, nights) tuple. Returns rows inserted.

    Retries once with a `rate_limit_backoff`-second sleep if fli signals
    HTTP 429 or rate-limit on the first attempt. Other FliErrors propagate
    to the caller without retry.
    """
    try:
        results = fli.search_dates(origin, dest, start_date, end_date, trip_nights)
    except FliError as e:
        if not _is_rate_limit_error(e):
            raise
        log.info(
            "%s->%s %dn rate-limited; backing off %.0fs and retrying once",
            origin, dest, trip_nights, rate_limit_backoff,
        )
        time.sleep(rate_limit_backoff)
        results = fli.search_dates(origin, dest, start_date, end_date, trip_nights)

    # Drop implausible fares (bad scrapes) before any write, so one error fare
    # can't skew the archive or a hub/comparison ranking.
    if results:
        kept = [r for r in results if _plausible(r.total_price_usd)]
        if len(kept) != len(results):
            log.warning("%s->%s %dn: dropped %d implausible fare(s) outside $%d-$%d",
                        origin, dest, trip_nights, len(results) - len(kept),
                        MIN_FARE_USD, MAX_FARE_USD)
        results = kept

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

        # Append one summary row to durable price_history (append-only, never
        # deleted). price_snapshots above is ephemeral ("what's cheap to book
        # now"); price_history accumulates the route's cheapest observed price
        # per scan day, which is what baseline computation reads. INSERT OR
        # REPLACE keyed on the UNIQUE constraint means re-running the same day
        # overwrites rather than duplicates.
        cheapest = min(r.total_price_usd for r in results)
        conn.execute(
            """INSERT OR REPLACE INTO price_history
               (origin_iata, dest_iata, trip_nights, cheapest_price_usd, observed_date, source)
               VALUES (?, ?, ?, ?, date('now'), 'fli')""",
            (origin, dest, trip_nights, cheapest),
        )

        # Append the FULL price surface to the durable fare_observations
        # archive (never deleted), so we keep every departure-date fare per
        # scan day, not just the single cheapest. INSERT OR REPLACE on the
        # UNIQUE key makes a same-day re-run idempotent.
        for r in results:
            conn.execute(
                """INSERT OR REPLACE INTO fare_observations
                   (origin_iata, dest_iata, departure_date, return_date,
                    trip_nights, total_price_usd, stops, carrier_codes,
                    source, observed_date, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), ?)""",
                (
                    r.origin_iata, r.dest_iata,
                    r.departure_date, r.return_date,
                    r.trip_nights, r.total_price_usd,
                    r.stops, json.dumps(r.carrier_codes) if r.carrier_codes else None,
                    "fli", fetched_at,
                ),
            )

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
        # Round-robin by destination so every origin gets coverage quickly.
        # Iterating origin-major means /go is empty for 11/12 origins for hours
        # while we churn through the first origin. Destination-major spreads
        # load: after ~3 minutes every origin has data for one destination.
        # Also less likely to trigger Google's per-origin rate limiter.
        pairs = conn.execute(
            "SELECT origin_iata, dest_iata FROM routes ORDER BY dest_iata, origin_iata"
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

    # Fact monitor: re-seed the curated pairings (idempotent) and re-verify every
    # claim against the fares we just collected, then alert if any broke or got
    # thin. Non-fatal — a monitor hiccup must not fail the price refresh itself.
    try:
        conn = sqlite3.connect(db_path)
        try:
            pairings.seed_pairings(conn)
            verify_summary = pairings.verify_all(conn, now=_iso_now())
            flagged = pairings.at_risk(conn)
        finally:
            conn.close()
        log.info("pairings verified: %s; %d at risk", verify_summary, len(flagged))
        if flagged:
            send_pairing_alert(flagged)
    except Exception:
        log.exception("pairing verification failed (non-fatal)")

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
