"""City-hub content assembly (W2 data layer).

A hub turns everything the engine + catalog know about one origin into the
content a hub page renders: a verified hero (from the pairing engine), the full
list of reachable trips ranked by all-in cost, and the cuts the page slices from
that list (cheapest, long-haul steals, by vibe). This module is pure data — no
HTML — so it stays testable and the generator/template can be thin.

`total cost` is the spine: airfare (best seen) + nights x avg daily on-ground.
That on-ground term is the insight the whole product rests on — the place that's
cheaper to FLY to is often dearer to BE in, and the all-in number reorders the
list (Sofia beats Las Vegas from Nashville; Tbilisi ties San Diego).
"""
import json
import logging
from typing import Optional

from server import pairings

log = logging.getLogger(__name__)

# Common-name override: the catalog stores the airport's city, which sometimes
# isn't how people say the place. The hub copy reads better with the common name.
# Presentation only — the engine still keys everything by IATA. (Per the W1
# review: the clean home for this is here in the hub layer, not the engine.)
DISPLAY_NAMES = {
    "AUA": "Aruba",          # catalog: Oranjestad
    "DPS": "Bali",           # catalog: Denpasar
    "NAN": "Fiji",           # catalog: Nadi
    "MLE": "the Maldives",   # catalog: Malé
}

# Regions close enough to read as a "normal" trip. Everything else is the
# long-haul reach the page is built to surprise people with.
NEARBY_REGIONS = {"North America", "Latin America", "Caribbean"}


def build_hub(conn, origin: str, nights: int = pairings.DEFAULT_NIGHTS,
              display_names: dict = DISPLAY_NAMES) -> dict:
    """Assemble the full hub content for one origin.

    Returns {origin, origin_city, hero, trips}. `trips` is every reachable
    destination with fare data, each a dict ready for the template, sorted by
    all-in cost ascending. `hero` is the verified pairing headline or None.
    """
    arow = conn.execute(
        "SELECT city FROM airports WHERE iata=?", (origin,)
    ).fetchone()
    origin_city = arow[0] if arow else origin

    rows = conn.execute(
        "SELECT d.iata, d.city, d.country, d.region, d.vibes, d.best_months, "
        "       d.avg_daily_cost_usd AS daily, MIN(ph.cheapest_price_usd) AS air "
        "FROM destinations d "
        "JOIN price_history ph ON ph.dest_iata = d.iata "
        "WHERE ph.origin_iata = ? AND ph.trip_nights = ? "
        "GROUP BY d.iata",
        (origin, nights),
    ).fetchall()

    trips = []
    for iata, city, country, region, vibes, best_months, daily, air in rows:
        trips.append({
            "iata": iata,
            "city": display_names.get(iata) or city,
            "country": country,
            "region": region,
            "airfare_usd": int(air),
            "daily_usd": int(daily),
            "nights": nights,
            "total_usd": int(air) + nights * int(daily),
            "vibes": _parse_json_list(vibes),
            "best_months": _parse_json_list(best_months),
            "overseas": region not in NEARBY_REGIONS,
        })
    trips.sort(key=lambda t: t["total_usd"])

    return {
        "origin": origin,
        "origin_city": origin_city,
        "hero": pairings.get_headline(conn, origin, display_names=display_names),
        "trips": trips,
    }


def cheapest_trips(hub: dict, n: int) -> list:
    """The n cheapest all-in trips."""
    return hub["trips"][:n]


def by_vibe(hub: dict, vibe: str, n: int) -> list:
    """The n cheapest trips tagged with `vibe`, cheapest first."""
    return [t for t in hub["trips"] if vibe in t["vibes"]][:n]


def long_haul_under(hub: dict, benchmark_usd: int, n: Optional[int] = None) -> list:
    """Overseas trips whose all-in cost comes in under a benchmark (typically the
    origin's anchor total). This is the "a week THERE costs less than a week in
    [domestic anchor]" surprise, cheapest first.
    """
    out = [t for t in hub["trips"] if t["overseas"] and t["total_usd"] < benchmark_usd]
    return out[:n] if n is not None else out


def _parse_json_list(raw) -> list:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []
