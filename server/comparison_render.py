"""Render a comparison dict (from server.comparisons.build_comparison) to HTML.

The brand's signature flip as a standalone, shareable page: the verified claim,
the why-it-flips explanation (ground cost is the hidden driver), a side-by-side
breakdown, and the cross-origin robustness proof. Per-page SEO + BreadcrumbList
schema; NO Offer/price markup (directional figures). Origin-agnostic: a "typical
US city" total, with the "cheaper from N of 12 cities" line carrying the rigor.
"""
import html
from typing import Optional

from server import schema_ld

CANONICAL_BASE = "https://promptiv.io"


def _esc(s) -> str:
    return html.escape(str(s))


def _money(n) -> str:
    return f"${int(n):,}"


def render_comparison(comp: dict, others: Optional[list] = None,
                      freshness: str = "", canonical_base: str = CANONICAL_BASE) -> str:
    cheap, anchor = comp["cheap"], comp["anchor"]
    nights = comp["nights"]
    slug = comp["slug"]
    canonical = f"{canonical_base}/vs/{slug}"
    title = f"{cheap['city']} vs {anchor['city']}: which week costs less? | Promptiv"
    meta_desc = (
        f"A week in {cheap['city']} runs about {_money(cheap['total'])} all in; a week in "
        f"{anchor['city']}, {_money(anchor['total'])}. Total cost, flights plus a week on the "
        f"ground, not just the fare. Cheaper from {comp['wins']} of {comp['origins']} US cities."
    )
    why = (
        f"{anchor['city']} is cheap to fly to and expensive to be in (about "
        f"{_money(anchor['daily'])} a day). {cheap['city']} is the reverse (about "
        f"{_money(cheap['daily'])} a day). Over {nights} days the ground cost decides it, "
        f"the part almost nobody prices in."
    )

    # Side-by-side breakdown rows.
    def row(label, cv, av, total=False):
        weight = "600" if total else "400"
        return (
            f'<tr><td style="padding:9px 0;border-bottom:1px solid var(--color-border);'
            f'color:var(--color-text-muted);font-size:14px;">{_esc(label)}</td>'
            f'<td style="padding:9px 0;border-bottom:1px solid var(--color-border);text-align:right;'
            f'font-weight:{weight};color:var(--color-text-primary);">{cv}</td>'
            f'<td style="padding:9px 0;border-bottom:1px solid var(--color-border);text-align:right;'
            f'font-weight:{weight};color:var(--color-text-primary);">{av}</td></tr>'
        )

    breakdown = (
        f'<tr><td></td>'
        f'<th style="text-align:right;font-family:var(--font-sans);font-size:13px;color:var(--color-text-secondary);padding-bottom:4px;">{_esc(cheap["city"])}</th>'
        f'<th style="text-align:right;font-family:var(--font-sans);font-size:13px;color:var(--color-text-secondary);padding-bottom:4px;">{_esc(anchor["city"])}</th></tr>'
        + row("Flight (typical)", _money(cheap["airfare"]), _money(anchor["airfare"]))
        + row(f"{nights} days on the ground", _money(nights*cheap["daily"]), _money(nights*anchor["daily"]))
        + row("Total, all in", f'<span style="color:var(--color-accent-bright);font-family:var(--font-serif);font-style:italic;font-size:1.2rem;">{_money(cheap["total"])}</span>',
              f'<span style="font-family:var(--font-serif);font-style:italic;font-size:1.2rem;">{_money(anchor["total"])}</span>', total=True)
    )

    others_links = ""
    for o in (others or []):
        others_links += f'<a href="/vs/{_esc(o["slug"])}" class="xlink">{_esc(o["label"])}</a>'

    fresh_line = f'<p class="fresh">Prices updated {_esc(freshness)}.</p>' if freshness else ""

    json_ld = schema_ld.breadcrumb_ld([
        ("Home", f"{canonical_base}/"),
        (f"{cheap['city']} vs {anchor['city']}", canonical),
    ])

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
    .cmp-hero {{ margin-bottom: 8px; }}
    .why {{ font-family: var(--font-sans); font-size: 15.5px; line-height: 1.65; color: var(--color-text-secondary); max-width: 60ch; margin: 0 0 22px; }}
    .fresh {{ font-family: var(--font-sans); font-size: 12.5px; color: var(--color-text-faint); margin: 14px 0 0; }}
    .breakdown {{ width: 100%; max-width: 460px; border-collapse: collapse; margin: 8px 0 18px; font-family: var(--font-sans); }}
    .proof {{ font-family: var(--font-sans); font-size: 14.5px; color: var(--color-text-primary); margin: 0 0 6px; }}
    .proof b {{ color: var(--color-accent-bright); font-weight: 600; }}
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
      <div class="brand">Promptiv<span class="brand-dot"></span></div>
    </header>

    <main>
      <section class="hero cmp-hero">
        <div class="eyebrow"><span>{_esc(comp["angle"]) if comp["angle"] else "Cheap trips, not cheap flights"}</span></div>
        <h1 class="display">A week in <em>{_esc(cheap["city"])}</em> costs less than a week in <em>{_esc(anchor["city"])}</em>.</h1>
        <p class="why">{_esc(why)}</p>

        <table class="breakdown">{breakdown}</table>

        <p class="proof">Cheaper from <b>{comp["wins"]} of {comp["origins"]}</b> US cities we track, by about {_money(comp["margin"])} all in.</p>
        {fresh_line}

        <div class="cta-row" style="margin-top:24px;">
          <a class="btn primary-cta" href="/go">See where your budget reaches &rarr;</a>
        </div>
      </section>

      <div class="more">
        <span class="label">More flips:</span>
        {others_links}
        <a href="/go" class="xlink">Build your own search &rarr;</a>
      </div>
    </main>

    <footer class="footer">&copy; 2026 Promptiv &middot; <a href="/privacy">Privacy</a> &middot; <a href="/terms">Terms</a></footer>
  </div>
</body>
</html>
"""
