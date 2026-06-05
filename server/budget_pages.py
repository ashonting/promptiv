"""Budget pages (origin x budget band) — the programmatic-SEO pilot.

The first page type in the lattice. Answers the core inversion query
("where can I go from <city> for under $X for a week, all in"), which static
listicles can't. Built from the same engine the hubs use, so it stays in sync.

Selectivity-first gating is the whole point: a page is generated only when the
band is a *real* filter — at least MIN_RESULTS destinations qualify (not thin)
AND no more than MAX_FRACTION of the catalog qualifies (else the page is just
the hub with a pointless filter, no information gain). That gate is what keeps
the lattice from becoming the kind of thin permutation dump Google demotes.

The per-page intro is a data-led composer (server-side, deterministic, varies by
real data). It's the seam where a richer LLM / content-pipeline pass plugs in.
"""
import datetime
from typing import Optional

from server import hubs
from server.hub_render import slugify

# Candidate bands. The gate decides which actually publish per origin.
BUDGET_BANDS = [750, 1000, 1500, 2000]
MIN_RESULTS = 8        # below this the page is thin -> suppress
MAX_FRACTION = 0.75    # above this the band ~= the whole catalog -> suppress



def build_budget_page(conn, origin: str, budget: int) -> Optional[dict]:
    """Assemble one origin x budget page, or None if the band is gated out
    (too thin or too broad to add value)."""
    hub = hubs.build_hub(conn, origin)
    trips = hub["trips"]
    total = len(trips)
    if total == 0:
        return None
    under = [t for t in trips if t["total_usd"] <= budget]
    if len(under) < MIN_RESULTS or len(under) > MAX_FRACTION * total:
        return None  # selectivity gate: not a useful filter

    origin_city = hub["origin_city"]
    return {
        "origin": origin,
        "origin_city": origin_city,
        "slug": slugify(origin_city),
        "budget": budget,
        "trips": under,
        "count": len(under),
        "catalog_total": total,
        "priciest": trips[-1],          # the "won't fit" anchor
        "hero": hub["hero"],
        "intro": compose_intro(origin_city, budget, under, trips),
    }


def published_bands(conn, origin: str) -> list:
    """The bands that actually publish for an origin (after gating)."""
    out = []
    for b in BUDGET_BANDS:
        if build_budget_page(conn, origin, b) is not None:
            out.append(b)
    return out


def _money(n) -> str:
    return f"${int(n):,}"


def _name_list(names: list) -> str:
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def compose_intro(origin_city: str, budget: int, under: list, all_trips: list) -> str:
    """Data-led, on-brand intro. Differentiated PER BAND so sibling pages don't
    cannibalize: the floor anchors it, but the "what this budget reaches" picks
    (the priciest still under budget) and the near-miss vary by band. This is the
    slot a content pipeline / LLM pass can replace for more polish.
    """
    n = len(under)
    floor = under[0]
    # Headliners: the priciest still-under-budget picks — what THIS budget buys
    # that a tighter one doesn't. Distinct per band.
    headliners = _name_list([t["city"] for t in under[-3:]])
    # The cheapest trip just over the line — useful, and band-specific.
    near = next((t for t in all_trips if t["total_usd"] > budget), None)

    sentences = [
        f"From {origin_city}, {n} destinations fit a full week under {_money(budget)}, "
        f"airfare plus seven days on the ground.",
        f"It starts at {floor['city']}, about {_money(floor['total_usd'])} all in.",
    ]
    if headliners:
        sentences.append(f"{_money(budget)} also reaches {headliners}.")
    if near:
        sentences.append(f"Just over the line: {near['city']} at {_money(near['total_usd'])}.")
    return " ".join(sentences)


def freshness_date() -> str:
    return datetime.date.today().isoformat()
