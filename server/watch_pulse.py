"""Weekly pulse: one Sunday email per user listing their active watches.
Idempotent per (watch, day) via watch_events kind='pulse'."""
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timezone

from server import email_client, watches, watch_brain, watch_emails

log = logging.getLogger("watch_pulse")
SLEEP_BETWEEN_SENDS = 0.4


def _trend(series):
    if len(series) < 4:
        return "flat"
    half = len(series) // 2
    a = sum(p for _, p in series[:half]) / half
    b = sum(p for _, p in series[half:]) / (len(series) - half)
    return "down" if b < a * 0.97 else ("up" if b > a * 1.03 else "flat")


def send_pulses(conn, base_url: str, today: date | None = None,
                sleep: float = SLEEP_BETWEEN_SENDS) -> int:
    today = today or date.today()
    cutoff = today.isoformat()
    by_email: dict[str, list[dict]] = {}
    for w in watches.active_watches(conn):
        sent = conn.execute(
            "SELECT 1 FROM watch_events WHERE watch_id=? AND kind='pulse' "
            "AND sent_at >= ?", (w["id"], cutoff)).fetchone()
        if sent:
            continue
        # everything observed so far (strictly before tomorrow = incl. today)
        series = watch_brain.series_for(conn, w, cutoff + "z")
        w = dict(w)
        w["_nights"] = len(series)
        if series:
            last_day = series[-1][0]
            best = watch_brain.nightly_best(conn, w, last_day)
            w["_best"] = best if best[0] is not None else (
                series[-1][1], w["window_start"], w["window_end"])
            w["_trend"] = _trend(series)
        else:
            w["_best"] = None
            w["_trend"] = "flat"
        by_email.setdefault(w["email"], []).append(w)

    sent_users = 0
    now = datetime.now(timezone.utc).isoformat()
    for email_addr, rows in by_email.items():
        msg = watch_emails.compose_pulse(rows, base_url=base_url)
        manage = f"{base_url}/watch/manage?token={rows[0]['manage_token']}"
        email_client.send_digest_email(email_addr, msg["subject"], msg["html"],
                                       msg["text"], unsubscribe_url=manage)
        for w in rows:
            conn.execute(
                "INSERT INTO watch_events (watch_id, kind, sent_at) VALUES (?,?,?)",
                (w["id"], "pulse", now))
        conn.commit()
        sent_users += 1
        if sleep:
            time.sleep(sleep)
    log.info("pulse: %d user emails sent", sent_users)
    return sent_users


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    db_path = os.environ.get("DATABASE_PATH", "./teaser.dev.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        send_pulses(conn, base_url=os.environ.get("BASE_URL", "https://dashaway.io"))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
