"""The alert brain: pure decision logic over a watch's nightly-best series.

Triggers (spec section 7): drop >=12% vs trailing-14-night low (night 2+);
bottom-15% percentile (night 14+); user ceiling (anytime).
Covenant: <=1 alert / 7 days, overridden only by a >=20% single-night drop.
Reports observed history only — never forecasts.
"""
from datetime import date

DROP_FACTOR = 0.88        # today <= 88% of trailing low  => drop trigger
OVERRIDE_FACTOR = 0.80    # today <= 80% of trailing low  => covenant override
TRAIL_NIGHTS = 14
PCTL_MIN_NIGHTS = 14
PCTL_BOTTOM = 0.15
COVENANT_DAYS = 7


def decide(series, today_best, ceiling, last_alert_at, today: date):
    """series: [(iso_date, best_price)] prior nights (may be empty).
    Returns None or {trigger, override, nights_watched, percentile, trailing_low}.
    """
    if today_best is None:
        return None
    prior = [p for _, p in series if p is not None]
    trailing = prior[-TRAIL_NIGHTS:]
    trailing_low = min(trailing) if trailing else None

    trigger = None
    if ceiling and today_best < ceiling:
        trigger = "ceiling"
    if trailing_low is not None and today_best <= DROP_FACTOR * trailing_low:
        trigger = "drop"   # drop outranks ceiling for messaging
    pct = None
    if len(prior) >= PCTL_MIN_NIGHTS:
        below = sum(1 for p in prior if p < today_best)
        pct = round(100.0 * below / (len(prior) + 1), 1)
        if trigger is None and pct <= PCTL_BOTTOM * 100:
            trigger = "percentile"
    if trigger is None:
        return None

    override = (trailing_low is not None
                and today_best <= OVERRIDE_FACTOR * trailing_low)
    if last_alert_at:
        last_day = date.fromisoformat(last_alert_at[:10])
        if (today - last_day).days < COVENANT_DAYS and not override:
            return None

    return {
        "trigger": trigger,
        "override": override,
        "nights_watched": len(prior) + 1,
        "percentile": pct,
        "trailing_low": trailing_low,
    }


def nightly_best(conn, watch, observed_date: str):
    """Tonight's cheapest (price, depart, return) inside the watch window,
    from fare_observations written by the watch runner."""
    row = conn.execute(
        """SELECT total_price_usd, departure_date, return_date
           FROM fare_observations
           WHERE origin_iata=? AND dest_iata=? AND trip_nights=?
             AND source='watch' AND observed_date=?
             AND departure_date >= ? AND departure_date <= ?
             AND total_price_usd IS NOT NULL
           ORDER BY total_price_usd ASC LIMIT 1""",
        (watch["origin_iata"], watch["dest_iata"], watch["trip_nights"],
         observed_date, watch["window_start"], watch["window_end"])).fetchone()
    return (row[0], row[1], row[2]) if row else (None, None, None)


def series_for(conn, watch, before_date: str):
    """Prior nightly bests [(observed_date, best_price)], oldest first."""
    rows = conn.execute(
        """SELECT observed_date, MIN(total_price_usd)
           FROM fare_observations
           WHERE origin_iata=? AND dest_iata=? AND trip_nights=?
             AND source='watch' AND observed_date < ?
             AND departure_date >= ? AND departure_date <= ?
             AND total_price_usd IS NOT NULL
           GROUP BY observed_date ORDER BY observed_date""",
        (watch["origin_iata"], watch["dest_iata"], watch["trip_nights"],
         before_date, watch["window_start"], watch["window_end"])).fetchall()
    return [(r[0], r[1]) for r in rows]
