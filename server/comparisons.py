"""Comparison pages — the link/authority layer.

Each page proves one surprising "total-cost flip": a week in an exotic /
assumed-expensive place costs less than a week in a famous / assumed-cheap one.
The flip is the brand's signature insight; the page makes it shareable, which is
how the lattice earns links.

Origin-agnostic: the headline uses a "typical US city" total (median airfare
across the 12 origins + a week on the ground), and the page proves robustness by
counting how many origins the flip holds from. The gate publishes only robust
flips (cheap < anchor from >= MIN_ROBUST origins), re-checked on every regen so a
broken flip auto-suppresses — same durable-creative + monitored-fact pattern as
the pairing engine. No Offer/price markup: the figures are directional.
"""
import statistics
from typing import Optional

from server.hubs import DISPLAY_NAMES
from server.hub_render import slugify

NIGHTS = 7
MIN_ROBUST = 10  # flip must hold from >= this many origins to publish

# (cheap_iata, anchor_iata, angle) — curated, surprising, data-verified flips.
CURATED_COMPARISONS = [
    ("MDE", "LAS", "The flight to Vegas is cheap. The week isn't."),
    ("MEX", "CUN", "Same country. The city beats the resort."),
    ("MID", "CUN", "Yucatán's quieter side, for hundreds less."),
    ("CTG", "PUJ", "Two Caribbean beach weeks. One costs far less."),
    ("OAX", "SJD", "Mexico's food capital vs the resort strip."),
    ("BKK", "HNL", "Halfway around the world, and still under Hawaii."),
    ("HAN", "HNL", "A week in Vietnam beats a week in Hawaii."),
    ("CAI", "MCO", "A week at the Pyramids costs about what a week at Disney does."),
    ("SOF", "KEF", "Europe's cheapest capital vs its most expensive."),
    ("LIM", "AUA", "World-class food vs the all-inclusive."),
    ("TBS", "SAN", "The Caucasus comes in under Southern California."),
    ("BOG", "LAS", "Another week Vegas quietly loses."),
]


def _dest(conn, iata: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT iata, city, country, avg_daily_cost_usd FROM destinations WHERE iata=?",
        (iata,),
    ).fetchone()
    if not row:
        return None
    return {"iata": row[0], "city": DISPLAY_NAMES.get(row[0]) or row[1],
            "country": row[2], "daily": int(row[3])}


def _airfare_by_origin(conn, iata: str, nights: int = NIGHTS) -> dict:
    """origin -> cheapest airfare to dest (per-origin floor)."""
    return {o: a for o, a in conn.execute(
        "SELECT origin_iata, MIN(cheapest_price_usd) FROM price_history "
        "WHERE dest_iata=? AND trip_nights=? GROUP BY origin_iata", (iata, nights))
        if a is not None}


def typical_total(conn, dest: dict, nights: int = NIGHTS):
    """(median airfare across origins, that + a week on the ground), or None."""
    airs = list(_airfare_by_origin(conn, dest["iata"], nights).values())
    if not airs:
        return None
    air = int(statistics.median(airs))
    return air, air + nights * dest["daily"]


def build_comparison(conn, cheap_iata: str, anchor_iata: str, angle: str = "") -> Optional[dict]:
    """Assemble one comparison, or None if it's gated out (missing data, the
    typical flip doesn't hold, or it isn't robust across origins)."""
    cheap = _dest(conn, cheap_iata)
    anchor = _dest(conn, anchor_iata)
    if not cheap or not anchor:
        return None
    ct = typical_total(conn, cheap)
    at = typical_total(conn, anchor)
    if not ct or not at:
        return None
    cheap_air, cheap_total = ct
    anchor_air, anchor_total = at

    cheap_by = _airfare_by_origin(conn, cheap_iata)
    anchor_by = _airfare_by_origin(conn, anchor_iata)
    shared = set(cheap_by) & set(anchor_by)
    wins = sum(1 for o in shared
               if cheap_by[o] + NIGHTS * cheap["daily"] < anchor_by[o] + NIGHTS * anchor["daily"])

    # Gate: the typical-city flip must hold AND be robust across origins.
    if cheap_total >= anchor_total or wins < MIN_ROBUST:
        return None

    return {
        "cheap": {**cheap, "airfare": cheap_air, "total": cheap_total},
        "anchor": {**anchor, "airfare": anchor_air, "total": anchor_total},
        "margin": anchor_total - cheap_total,
        "wins": wins,
        "origins": len(shared),
        "nights": NIGHTS,
        "angle": angle,
        "slug": f"{slugify(cheap['city'])}-vs-{slugify(anchor['city'])}",
    }


def published_comparisons(conn) -> list:
    """The curated comparisons that pass the gate, in curated order."""
    out = []
    for cheap, anchor, angle in CURATED_COMPARISONS:
        c = build_comparison(conn, cheap, anchor, angle)
        if c:
            out.append(c)
    return out
