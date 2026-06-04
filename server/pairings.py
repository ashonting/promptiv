"""Pairing engine + fact monitor (W1).

A pairing is the durable creative: from a given origin, "a week in <cheap>
costs less than a week in <anchor>." The pairing (the three IATAs) is curated by
hand and stable across refreshes. The dollar figures behind the claim are FACTS,
not creative — they drift as fares move, so verify_all() recomputes them on every
fare refresh and only marks a pairing `verified` when the cheap leg genuinely
costs less. get_headline() refuses to serve an unverified pairing, so we never
publish a claim the data does not back. at_risk() surfaces pairings whose claim
broke or whose margin got thin, for a human to re-pair.

Total trip cost = best airfare seen + nights x avg daily on-ground cost. That
on-ground term is the whole insight: the destination that is cheaper to FLY to
is often dearer to BE in, and the all-in number flips the ranking.
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)

DEFAULT_NIGHTS = 7

# A claim needs daylight, not a $1 edge that fare noise can flip overnight. Below
# this all-in margin the pairing is "at risk" and gets surfaced for re-pairing.
MIN_MARGIN_USD = 75

# The durable creative: (origin, cheap_dest, anchor_dest). Hand-curated from the
# BNA-led data exploration; stable across refreshes. Dollar figures are
# deliberately absent — those are facts, recomputed by verify_all().
CURATED_PAIRINGS = [
    ("BNA", "MDE", "LAS"),  # Medellín vs Las Vegas
    ("JFK", "MEX", "HNL"),  # Mexico City vs Honolulu
    ("LAX", "OAX", "SJD"),  # Oaxaca vs Los Cabos
    ("ATL", "CTG", "JAC"),  # Cartagena vs Jackson Hole
    ("DFW", "MID", "SJD"),  # Mérida vs Los Cabos
    ("ORD", "GUA", "HNL"),  # Guatemala City vs Honolulu
    ("MIA", "LIM", "AUA"),  # Lima vs Aruba
    ("SEA", "PTY", "HNL"),  # Panama City vs Honolulu
    ("DEN", "BOG", "JAC"),  # Bogotá vs Jackson Hole
    ("IAH", "SJO", "JAC"),  # San José vs Jackson Hole
    ("SFO", "SOF", "JAC"),  # Sofia vs Jackson Hole
    ("BOS", "CAI", "HNL"),  # Cairo vs Honolulu
]


def total_cost(conn, origin: str, dest: str, nights: int = DEFAULT_NIGHTS) -> Optional[int]:
    """All-in trip cost: best airfare ever seen + nights x avg daily cost.

    Returns None when we have no fare for the route or no daily cost for the
    destination — either way there is no defensible number to make a claim from.
    """
    row = conn.execute(
        "SELECT MIN(cheapest_price_usd) FROM price_history "
        "WHERE origin_iata=? AND dest_iata=? AND trip_nights=?",
        (origin, dest, nights),
    ).fetchone()
    airfare = row[0] if row else None
    if airfare is None:
        return None
    drow = conn.execute(
        "SELECT avg_daily_cost_usd FROM destinations WHERE iata=?", (dest,)
    ).fetchone()
    if drow is None or drow[0] is None:
        return None
    return int(airfare) + nights * int(drow[0])


def seed_pairings(conn, pairings=CURATED_PAIRINGS) -> None:
    """Insert the curated pairings. Idempotent: INSERT OR IGNORE never clobbers
    an existing row's computed facts, so re-seeding every refresh is safe."""
    for origin, cheap, anchor in pairings:
        conn.execute(
            "INSERT OR IGNORE INTO city_pairings "
            "(origin_iata, cheap_iata, anchor_iata, trip_nights, verified) "
            "VALUES (?, ?, ?, ?, 0)",
            (origin, cheap, anchor, DEFAULT_NIGHTS),
        )
    conn.commit()


def verify_all(conn, now: Optional[str] = None) -> dict:
    """Recompute both legs for every pairing and update verified flag + margin.

    A pairing is verified only when both legs have fare data AND the cheap leg's
    all-in cost is strictly lower. margin_usd is anchor_total - cheap_total
    (positive when the claim holds, negative when it is broken, None when a leg
    has no data). Returns counts of {verified, broken, unknown}.
    """
    rows = conn.execute(
        "SELECT origin_iata, cheap_iata, anchor_iata, trip_nights FROM city_pairings"
    ).fetchall()
    counts = {"verified": 0, "broken": 0, "unknown": 0}
    for origin, cheap, anchor, nights in rows:
        cheap_total = total_cost(conn, origin, cheap, nights)
        anchor_total = total_cost(conn, origin, anchor, nights)
        if cheap_total is None or anchor_total is None:
            ok, margin = 0, None
            counts["unknown"] += 1
        else:
            margin = anchor_total - cheap_total
            if cheap_total < anchor_total:
                ok = 1
                counts["verified"] += 1
            else:
                ok = 0
                counts["broken"] += 1
        conn.execute(
            "UPDATE city_pairings SET cheap_total_usd=?, anchor_total_usd=?, "
            "margin_usd=?, verified=?, last_checked=? WHERE origin_iata=?",
            (cheap_total, anchor_total, margin, ok, now, origin),
        )
    conn.commit()
    return counts


def get_headline(conn, origin: str, display_names: Optional[dict] = None) -> Optional[dict]:
    """The served headline for an origin, or None if the pairing is not verified.

    The verified gate is the whole point: an unbacked claim is never published.
    City names default to the destinations catalog so the text stays in sync with
    the data; pass `display_names` (IATA -> common name) to override the few cases
    where the catalog's airport-city differs from how people say the place
    (e.g. AUA "Oranjestad" -> "Aruba"). The override is a presentation concern, so
    the map lives in the consuming layer (see server/hubs.py), not here.
    """
    row = conn.execute(
        "SELECT cheap_iata, anchor_iata, cheap_total_usd, anchor_total_usd, margin_usd "
        "FROM city_pairings WHERE origin_iata=? AND verified=1",
        (origin,),
    ).fetchone()
    if row is None:
        return None
    names = display_names or {}
    cheap_iata, anchor_iata, cheap_total, anchor_total, margin = row
    cheap_city = names.get(cheap_iata) or _city(conn, cheap_iata)
    anchor_city = names.get(anchor_iata) or _city(conn, anchor_iata)
    if cheap_city is None or anchor_city is None:
        return None
    return {
        "origin": origin,
        "cheap_iata": cheap_iata,
        "anchor_iata": anchor_iata,
        "cheap_city": cheap_city,
        "anchor_city": anchor_city,
        "cheap_total_usd": cheap_total,
        "anchor_total_usd": anchor_total,
        "margin_usd": margin,
        "headline": f"A week in {cheap_city} costs less than a week in {anchor_city}.",
    }


def at_risk(conn, min_margin: int = MIN_MARGIN_USD) -> list:
    """Pairings the monitor wants a human to look at: the claim broke (both legs
    priced but cheap >= anchor) or the margin got thin (verified but under
    min_margin). Unknown / no-data pairings are excluded — there is nothing to
    re-pair until fares arrive. Ordered thinnest/most-broken first.
    """
    rows = conn.execute(
        "SELECT origin_iata, cheap_iata, anchor_iata, cheap_total_usd, "
        "anchor_total_usd, margin_usd, verified FROM city_pairings "
        "WHERE cheap_total_usd IS NOT NULL AND anchor_total_usd IS NOT NULL "
        "AND (verified=0 OR margin_usd < ?) ORDER BY margin_usd",
        (min_margin,),
    ).fetchall()
    out = []
    for origin, cheap, anchor, cheap_total, anchor_total, margin, verified in rows:
        out.append({
            "origin": origin,
            "cheap_iata": cheap,
            "anchor_iata": anchor,
            "cheap_total_usd": cheap_total,
            "anchor_total_usd": anchor_total,
            "margin_usd": margin,
            "reason": "thin_margin" if verified else "broken",
        })
    return out


def _city(conn, iata: str) -> Optional[str]:
    row = conn.execute(
        "SELECT city FROM destinations WHERE iata=?", (iata,)
    ).fetchone()
    return row[0] if row else None
