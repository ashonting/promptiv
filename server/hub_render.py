"""Render a hub dict (from server.hubs.build_hub) to a static HTML page.

Pure string rendering — no framework. Reuses the site's styles.css and the
editorial brand language (Instrument Serif display, Inter body, violet accent,
trips as typographic rows, not cards). Per-hub SEO is baked into <head>: a unique
title, meta description, Open Graph, and a self-canonical, because each hub is a
real indexed page and the actual ranking surface.
"""
import html
from typing import Optional

from server import hubs

CANONICAL_BASE = "https://promptiv.io"

# How many entries each section shows.
N_CHEAPEST = 10
N_LONG_HAUL = 6
VIBE_CUTS = [
    ("beach", "Beach"),
    ("food", "Food"),
    ("nightlife", "Nightlife"),
    ("nature", "Nature"),
    ("history", "History"),
]


def slugify(city: str) -> str:
    """Hub URL slug from a city name: 'Nashville' -> 'nashville'."""
    return "".join(c if c.isalnum() else "-" for c in city.lower()).strip("-")


def _money(n) -> str:
    return f"${n:,}"


def _esc(s) -> str:
    return html.escape(str(s))


def render_hub(hub: dict, canonical_base: str = CANONICAL_BASE) -> str:
    origin_city = hub["origin_city"]
    slug = slugify(origin_city)
    canonical = f"{canonical_base}/{slug}"
    hero = hub["hero"]

    title = f"Cheap trips from {origin_city} | Promptiv"
    if hero:
        meta_desc = (
            f"A week in {hero['cheap_city']} costs less than a week in "
            f"{hero['anchor_city']}. See where your budget actually reaches from "
            f"{origin_city}, total trip cost, not just airfare."
        )
    else:
        meta_desc = (
            f"See where your budget actually reaches from {origin_city}. "
            f"Total trip cost, not just airfare."
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
  <link rel="stylesheet" href="/styles.css" />
  <style>
    .hub-hero {{ margin-bottom: 8px; }}
    .hub-section {{ margin: 56px 0 0; }}
    .hub-section h2 {{
      font-family: var(--font-serif); font-weight: 400; font-style: italic;
      font-size: clamp(1.6rem, 3vw, 2.1rem); line-height: 1.1;
      color: var(--color-text-primary); margin: 0 0 6px;
    }}
    .hub-section .section-note {{
      font-family: var(--font-sans); font-size: 14px; color: var(--color-text-muted);
      margin: 0 0 22px; max-width: 56ch; line-height: 1.6;
    }}
    .trip-list {{ list-style: none; margin: 0; padding: 0; }}
    .trip {{
      display: flex; align-items: baseline; justify-content: space-between;
      gap: 16px; padding: 13px 0; border-bottom: 1px solid var(--color-border);
    }}
    .trip:last-child {{ border-bottom: none; }}
    .trip-place {{ font-family: var(--font-sans); font-size: 16px; color: var(--color-text-primary); }}
    .trip-place .country {{ color: var(--color-text-muted); font-size: 14px; }}
    .trip-break {{ display: block; font-size: 12.5px; color: var(--color-text-faint); margin-top: 2px; }}
    .trip-total {{
      font-family: var(--font-serif); font-style: italic; font-size: 1.45rem;
      color: var(--color-accent-bright); white-space: nowrap;
    }}
    .vibe-list {{ list-style: none; margin: 0; padding: 0; }}
    .vibe-row {{
      display: flex; align-items: baseline; gap: 14px; padding: 11px 0;
      border-bottom: 1px solid var(--color-border); font-family: var(--font-sans);
    }}
    .vibe-row:last-child {{ border-bottom: none; }}
    .vibe-tag {{
      font-size: 12px; text-transform: uppercase; letter-spacing: .08em;
      color: var(--color-text-muted); width: 92px; flex: none;
    }}
    .vibe-pick {{ color: var(--color-text-primary); font-size: 15px; }}
    .vibe-pick b {{ color: var(--color-accent-bright); font-weight: 500; }}
    .hub-back {{
      font-family: var(--font-sans); font-size: 13px; color: var(--color-text-muted);
      text-decoration: none;
    }}
    .hub-back:hover {{ color: var(--color-text-secondary); }}
  </style>
</head>
<body>
  <div class="aurora"></div>
  <div class="frame">
    <header class="top-bar">
      <div class="brand">Promptiv<span class="brand-dot"></span></div>
      <a class="hub-back" href="/">&larr; All cities</a>
    </header>

    <main>
      <section class="hero hub-hero">
        <div class="eyebrow"><span>Cheap trips from {_esc(origin_city)}</span></div>
        {_hero_headline_html(hero, origin_city)}
        <p class="lede">Total trip cost, airfare plus a week on the ground, not just the
          fare. That's the number that actually decides where you can afford to go.</p>
        <form id="signup-form" class="form secondary-form" action="/api/signup" method="POST" novalidate>
          <input type="hidden" name="hub_city" value="{_esc(origin_city)}" />
          <label for="email-input" class="sr-only">Your email</label>
          <input id="email-input" class="email" type="email" name="email"
                 placeholder="get {_esc(origin_city)}&rsquo;s cheapest trips, weekly" required autocomplete="email" />
          <button class="btn-secondary" type="submit">Notify me</button>
        </form>
        <p id="signup-confirm" class="lede" hidden>You&rsquo;re on the list. We&rsquo;ll send {_esc(origin_city)}&rsquo;s cheapest trips weekly.</p>
      </section>

      {_cheapest_section(hub)}
      {_long_haul_section(hub)}
      {_vibe_section(hub)}
    </main>

    <footer class="footer">&copy; 2026 Promptiv &middot; <a href="/privacy">Privacy</a> &middot; <a href="/terms">Terms</a></footer>
  </div>

  <script src="/app.js"></script>
</body>
</html>
"""


def _hero_headline_html(hero: Optional[dict], origin_city: str) -> str:
    if hero:
        return (
            f'<h1 class="display">A week in <em>{_esc(hero["cheap_city"])}</em> '
            f'costs less than a week in <em>{_esc(hero["anchor_city"])}</em>.</h1>'
        )
    return f'<h1 class="display">See where your budget reaches from <em>{_esc(origin_city)}</em>.</h1>'


def _cheapest_section(hub: dict) -> str:
    rows = []
    for t in hubs.cheapest_trips(hub, N_CHEAPEST):
        rows.append(
            '<li class="trip">'
            f'<span class="trip-place">{_esc(t["city"])}<span class="country">, {_esc(t["country"])}</span>'
            f'<span class="trip-break">flight {_money(t["airfare_usd"])} + {_money(t["daily_usd"])}/day for a week</span>'
            '</span>'
            f'<span class="trip-total">{_money(t["total_usd"])}</span>'
            '</li>'
        )
    return (
        '<section class="hub-section">'
        f'<h2>The cheapest weeks from {_esc(hub["origin_city"])}</h2>'
        '<p class="section-note">Ranked by what the whole week actually costs. A cheap flight '
        'to an expensive city loses to a pricier flight somewhere your money goes further.</p>'
        f'<ul class="trip-list">{"".join(rows)}</ul>'
        '</section>'
    )


def _long_haul_section(hub: dict) -> str:
    hero = hub["hero"]
    if not hero:
        return ""
    benchmark = hero["anchor_total_usd"]
    picks = hubs.long_haul_under(hub, benchmark, N_LONG_HAUL)
    if not picks:
        return ""
    rows = []
    for t in picks:
        rows.append(
            '<li class="trip">'
            f'<span class="trip-place">{_esc(t["city"])}<span class="country">, {_esc(t["country"])}</span>'
            f'<span class="trip-break">flight {_money(t["airfare_usd"])} + {_money(t["daily_usd"])}/day for a week</span>'
            '</span>'
            f'<span class="trip-total">{_money(t["total_usd"])}</span>'
            '</li>'
        )
    return (
        '<section class="hub-section">'
        '<h2>Farther than you think, cheaper than you&rsquo;d guess</h2>'
        f'<p class="section-note">Every one of these overseas weeks comes in under a week in '
        f'{_esc(hero["anchor_city"])} ({_money(benchmark)}, all in). Distance is not the same as price.</p>'
        f'<ul class="trip-list">{"".join(rows)}</ul>'
        '</section>'
    )


def _vibe_section(hub: dict) -> str:
    rows = []
    for vibe, label in VIBE_CUTS:
        picks = hubs.by_vibe(hub, vibe, 1)
        if not picks:
            continue
        t = picks[0]
        rows.append(
            '<li class="vibe-row">'
            f'<span class="vibe-tag">{_esc(label)}</span>'
            f'<span class="vibe-pick">A week in <b>{_esc(t["city"])}</b>, {_money(t["total_usd"])}</span>'
            '</li>'
        )
    if not rows:
        return ""
    return (
        '<section class="hub-section">'
        '<h2>Whatever you&rsquo;re after</h2>'
        '<p class="section-note">The cheapest week, all in, for each kind of trip.</p>'
        f'<ul class="vibe-list">{"".join(rows)}</ul>'
        '</section>'
    )
