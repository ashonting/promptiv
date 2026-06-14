"""Nightly watch scan: one paced SearchDates request per distinct watched route.

Spec rules honored here:
- pacing between requests (politeness; shares the warmed IP with the refresh)
- plausibility guard reused from price_refresh
- ANY 429 aborts the entire night (never retry into a block) + ops alert
- alerts via watch_brain decisions; covenant enforced via last_alert_at
- ops summary email at the end of every run
"""
import json
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from server import email_client, watches, watch_brain, watch_emails
from server.price_refresh import _plausible

log = logging.getLogger("watch_runner")

SLEEP_BETWEEN_CALLS = 6.0
RUNTIME_TRIPWIRE_S = 3 * 3600
ERROR_RATE_TRIPWIRE = 0.10


def _is_429(err) -> bool:
    m = str(err).lower()
    return "429" in m or "rate-limit" in m or "rate limit" in m


def _ops_email(subject: str, body: str) -> None:
    to = os.environ.get("OPS_EMAIL") or os.environ.get("RESEND_REPLY_TO")
    if not to:
        log.warning("no OPS_EMAIL configured; ops note: %s", subject)
        return
    email_client.send_digest_email(to, subject, f"<pre>{body}</pre>", body)


def run(conn, fli=None, sleep_s: float = SLEEP_BETWEEN_CALLS,
        today: date | None = None, base_url: str = "https://dashaway.io") -> dict:
    today = today or date.today()
    observed = today.isoformat()
    fetched_at = datetime.now(timezone.utc).isoformat()
    if fli is None:
        from server.fli_client import FliClient
        fli = FliClient()

    active = watches.active_watches(conn)
    groups: dict[tuple, list[dict]] = {}
    for w in active:
        key = (w["origin_iata"], w["dest_iata"], w["window_start"],
               w["window_end"], w["trip_nights"])
        groups.setdefault(key, []).append(w)

    t0 = time.monotonic()
    tomorrow = today + timedelta(days=1)
    summary = {"watches": len(active), "routes": len(groups), "scanned": 0,
               "errors": 0, "alerts": 0, "obs_written": 0, "empty_routes": 0,
               "expired": 0, "aborted_429": False}

    for i, ((origin, dest, ws, we, nights), members) in enumerate(groups.items()):
        # Windows age: a stored window_start that has slipped into the past is
        # an invalid departure date. Clamp the query to tomorrow; if the whole
        # window is gone, the trip can't happen — expire the watch.
        search_start = max(date.fromisoformat(ws), tomorrow)
        search_end = date.fromisoformat(we)
        if search_start > search_end:
            for w in members:
                conn.execute("UPDATE watches SET status='expired' WHERE id=?",
                             (w["id"],))
            conn.commit()
            summary["expired"] += len(members)
            log.info("%s->%s window fully past; expired %d watch(es)",
                     origin, dest, len(members))
            continue
        try:
            results = fli.search_dates(origin, dest, search_start,
                                       search_end, nights)
        except Exception as e:
            if _is_429(e):
                summary["aborted_429"] = True
                log.error("429 from Google on %s->%s; ABORTING the night", origin, dest)
                _ops_email("WATCHES: 429 — night aborted",
                           f"429 on {origin}->{dest} after {summary['scanned']} "
                           f"routes. Job stopped to protect the IP. {e}")
                break
            summary["errors"] += 1
            summary["scanned"] += 1
            log.warning("%s->%s scan error (skipping route): %s", origin, dest, e)
            continue

        kept = [r for r in (results or []) if _plausible(r.total_price_usd)]
        for r in kept:
            conn.execute(
                """INSERT OR REPLACE INTO fare_observations
                   (origin_iata, dest_iata, departure_date, return_date,
                    trip_nights, total_price_usd, stops, carrier_codes,
                    source, observed_date, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?, 'watch', ?, ?)""",
                (r.origin_iata, r.dest_iata, r.departure_date, r.return_date,
                 r.trip_nights, r.total_price_usd, r.stops,
                 json.dumps(r.carrier_codes) if r.carrier_codes else None,
                 observed, fetched_at))
        conn.commit()
        summary["scanned"] += 1
        summary["obs_written"] += len(kept)
        if not kept:
            summary["empty_routes"] += 1
            log.warning("%s->%s returned EMPTY (possible soft-block)", origin, dest)

        for w in members:
            best = watch_brain.nightly_best(conn, w, observed)
            if best[0] is None:
                continue
            series = watch_brain.series_for(conn, w, observed)
            decision = watch_brain.decide(
                series, best[0], w["ceiling_usd"], w["last_alert_at"], today)
            if not decision:
                continue
            msg = watch_emails.compose_alert(conn, w, decision, best, base_url)
            manage = f"{base_url}/watch/manage?token={w['manage_token']}"
            email_client.send_digest_email(
                w["email"], msg["subject"], msg["html"], msg["text"],
                unsubscribe_url=manage)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO watch_events (watch_id, kind, sent_at, best_price,"
                " best_depart, best_return, trigger) VALUES (?,?,?,?,?,?,?)",
                (w["id"], "alert", now, best[0], best[1], best[2],
                 decision["trigger"]))
            conn.execute("UPDATE watches SET last_alert_at=? WHERE id=?",
                         (now, w["id"]))
            conn.commit()
            summary["alerts"] += 1

        if i + 1 < len(groups) and sleep_s:
            time.sleep(sleep_s)

    runtime = time.monotonic() - t0
    summary["runtime_s"] = round(runtime)
    tripwires = []
    if runtime > RUNTIME_TRIPWIRE_S:
        tripwires.append(f"runtime {runtime / 3600:.1f}h > 3h")
    if summary["scanned"] and summary["errors"] / summary["scanned"] > ERROR_RATE_TRIPWIRE:
        tripwires.append(f"error rate {summary['errors']}/{summary['scanned']}")
    if summary["scanned"] and summary["empty_routes"] == summary["scanned"]:
        tripwires.append(
            f"ALL {summary['scanned']} route(s) returned empty (possible soft-block)")
    body = json.dumps(summary, indent=2)
    subject = ("WATCHES tripwire: " + "; ".join(tripwires)) if tripwires else \
              (f"watches nightly: {summary['scanned']} routes, "
               f"{summary['alerts']} alerts")
    if not summary["aborted_429"]:        # 429 already sent its own ops email
        _ops_email(subject, body)
    log.info("watch run done: %s", summary)
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    db_path = os.environ.get("DATABASE_PATH", "./teaser.dev.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
