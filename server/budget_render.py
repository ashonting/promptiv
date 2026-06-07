"""Render a budget page (from server.budget_pages.build_budget_page) to static HTML.

Mirrors the hub page's editorial style and per-page SEO. Adds the things that
make a programmatic page legitimate rather than thin: a data-led intro, a
"prices updated" freshness line (which the daily regen actually earns), a real
internal-link graph (hub + sibling bands + the tool), and a city-tagged signup
so the page also feeds the weekly digest.
"""
import html
from typing import Optional

from server import schema_ld

CANONICAL_BASE = "https://dashaway.io"


def _esc(s) -> str:
    return html.escape(str(s))


def _money(n) -> str:
    return f"${int(n):,}"


def render_budget_page(page: dict, sibling_bands: Optional[list] = None,
                       freshness: str = "", canonical_base: str = CANONICAL_BASE) -> str:
    city = page["origin_city"]
    slug = page["slug"]
    budget = page["budget"]
    canonical = f"{canonical_base}/{slug}/under-{budget}"
    title = f"Trips under {_money(budget)} from {city} | DashAway"
    meta_desc = (
        f"{page['count']} trips from {city} that fit a full week under {_money(budget)}, "
        f"airfare plus a week on the ground. Total cost, not just the fare. Updated weekly."
    )

    sibling_links = ""
    for b in (sibling_bands or []):
        if b == budget:
            continue
        sibling_links += (
            f'<a href="/{_esc(slug)}/under-{b}" class="xlink">Under {_money(b)}</a>'
        )

    rows = []
    for t in page["trips"]:
        rows.append(
            '<li class="trip">'
            f'<span class="trip-place">{_esc(t["city"])}<span class="country">, {_esc(t["country"])}</span>'
            f'<span class="trip-break">flight {_money(t["airfare_usd"])} + {_money(t["daily_usd"])}/day for a week</span>'
            '</span>'
            f'<span class="trip-total">{_money(t["total_usd"])}</span>'
            '</li>'
        )

    fresh_line = f'<p class="fresh">Prices updated {_esc(freshness)}.</p>' if freshness else ""

    json_ld = schema_ld.page_ld(
        crumbs=[("Home", f"{canonical_base}/"),
                (city, f"{canonical_base}/{slug}"),
                (f"Trips under {_money(budget)}", canonical)],
        list_name=f"Trips under {_money(budget)} from {city}",
        item_names=[f"{t['city']}, {t['country']}" for t in page["trips"]],
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(meta_desc)}" />

  <meta property="og:title" content="{_esc(title)}" />
  <meta property="og:description" content="{_esc(meta_desc)}" />
  <meta property="og:url" content="{_esc(canonical)}" />
  <meta property="og:type" content="website" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">

  <link rel="canonical" href="{_esc(canonical)}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="/styles.css" />
  <style>
    .budget-hero {{ margin-bottom: 8px; }}
    .intro {{ font-family: var(--font-sans); font-size: 15.5px; line-height: 1.65; color: var(--color-text-secondary); max-width: 60ch; margin: 0 0 14px; }}
    .fresh {{ font-family: var(--font-sans); font-size: 12.5px; color: var(--color-text-faint); margin: 0 0 26px; }}
    .hub-section {{ margin: 40px 0 0; }}
    .hub-section h2 {{ font-family: var(--font-serif); font-weight: 400; font-style: italic; font-size: clamp(1.5rem, 3vw, 2rem); color: var(--color-text-primary); margin: 0 0 16px; }}
    .trip-list {{ list-style: none; margin: 0; padding: 0; }}
    .trip {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; padding: 13px 0; border-bottom: 1px solid var(--color-border); }}
    .trip:last-child {{ border-bottom: none; }}
    .trip-place {{ font-family: var(--font-sans); font-size: 16px; color: var(--color-text-primary); }}
    .trip-place .country {{ color: var(--color-text-muted); font-size: 14px; }}
    .trip-break {{ display: block; font-size: 12.5px; color: var(--color-text-faint); margin-top: 2px; }}
    .trip-total {{ font-family: var(--font-serif); font-style: italic; font-size: 1.45rem; color: var(--color-accent-bright); white-space: nowrap; }}
    .more {{ margin: 40px 0 0; font-family: var(--font-sans); font-size: 14px; }}
    .more .label {{ color: var(--color-text-muted); margin-right: 10px; }}
    .xlink {{ color: var(--color-text-secondary); font-weight: 500; margin-right: 14px; white-space: nowrap; }}
  </style>
  {json_ld}
</head>
<body>
  <div class="aurora"></div>
  <div class="frame">
    <header class="top-bar">
      <div class="brand">DashAway<span class="brand-dot"></span></div>
    </header>

    <main>
      <section class="hero budget-hero">
        <div class="eyebrow"><span>Cheap trips from {_esc(city)}</span></div>
        <h1 class="display">A week under <em>{_money(budget)}</em> from {_esc(city)}.</h1>
        <p class="intro">{_esc(page["intro"])}</p>
        {fresh_line}
        <form id="signup-form" class="form secondary-form" action="/api/signup" method="POST" novalidate>
          <input type="hidden" name="hub_city" value="{_esc(city)}" />
          <label for="email-input" class="sr-only">Your email</label>
          <input id="email-input" class="email" type="email" name="email"
                 placeholder="get {_esc(city)}&rsquo;s cheapest trips, weekly" required autocomplete="email" />
          <button class="btn-secondary" type="submit">Notify me</button>
        </form>
        <p id="signup-confirm" class="intro" hidden>You&rsquo;re on the list. We&rsquo;ll send {_esc(city)}&rsquo;s cheapest trips weekly.</p>
      </section>

      <section class="hub-section">
        <h2>Every week under {_money(budget)} from {_esc(city)}</h2>
        <ul class="trip-list">{"".join(rows)}</ul>
      </section>

      <div class="more">
        <span class="label">More from {_esc(city)}:</span>
        <a href="/{_esc(slug)}" class="xlink">All cheap trips</a>
        {sibling_links}
        <a href="/go" class="xlink">Build your own search &rarr;</a>
      </div>
    </main>

    <footer class="footer">&copy; 2026 DashAway &middot; <a href="/privacy">Privacy</a> &middot; <a href="/terms">Terms</a></footer>
  </div>

  <script src="/app.js"></script>
</body>
</html>
"""
