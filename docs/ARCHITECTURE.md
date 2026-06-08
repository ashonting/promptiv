# DashAway — System Architecture & Current State

**Last updated:** 2026-06-07 · Single source of truth for how DashAway works today.
For the product *why*, read `PRODUCT-BRIEF.md`. For the strategic pivot narrative,
`docs/plans/2026-06-04-cheap-trips-pivot.md`. For deploy mechanics, `deploy/DEPLOY.md`.

> **Rebrand (2026-06-07):** the product is now **DashAway** at **https://dashaway.io**
> (was "Promptiv" at promptiv.io). promptiv.io now serves a separate "Promptiv coming soon"
> placeholder (`/srv/promptiv-comingsoon/`). **Only the user-facing brand + domain flipped** —
> the local dir (`~/promptiv`), server path (`/srv/promptiv`), GitHub repo (`ashonting/promptiv`),
> systemd units (`promptiv-*`), and the `PROMPTIV_PAIRINGS` JS global kept their old names. nginx
> now serves two vhosts from one droplet (`deploy/nginx-dashaway.conf`). Some older references
> below + in `DEPLOY.md` still say "promptiv.io" — stale, update opportunistically.

---

## 1. What DashAway is

A curated **"cheap trips, not cheap flights"** product for **12 U.S. departure cities**.
It answers the question flight search doesn't: *from your city, where does your budget
actually reach for a great week, all-in?*

**The insight (the whole product):** total trip cost = **airfare + 7 × estimated daily
on-ground cost**. The destination that's cheaper to *fly to* is often dearer to *be in*,
and the all-in number flips the ranking. A week in Medellín costs less than a week in Las
Vegas. Nobody surfaces this because it requires fusing live fares with curated destination
economics — the asset we accumulate daily.

**The moat:** the inversion + an accumulating fare archive × curated destination metadata.
Freshness (we re-price daily) is a real edge over static listicles.

**Scope honesty:** we price *flights* (real) + *ground cost* (our estimate) + *curation*.
We do **not** aggregate live hotels/activities. Figures are directional ("about $820"),
never bookable quotes.

---

## 2. Stack & where it lives

| | Local | Production |
|---|---|---|
| Code | `~/promptiv/` (git, master) | `/srv/promptiv/` on `root@promptiv.io` (159.65.161.102, 1 GB RAM) |
| Python | `.venv/` (3.11) | `.venv/` (3.10) |
| DB | `teaser.dev.sqlite` | `/var/lib/promptiv/teaser.sqlite` (SQLite; `sqlite3` CLI NOT installed — use the venv python) |
| Web | static `public/` + Flask | nginx serves `public/`, proxies `/api/*` + `/unsubscribe` to gunicorn `:8000` |

Email via **Resend** (`team@mail.distillworks.com`). nginx config lives at
`/etc/nginx/sites-enabled/dashaway` (the repo's `deploy/nginx-dashaway.conf` is the
source; **it had diverged once — keep them in sync**).

---

## 3. Data model (`server/migrations.py`)

| Table | Role |
|---|---|
| `airports` | The 12 U.S. origins (iata, city, lat/lng). |
| `destinations` | ~100 curated destinations: daily cost, vibes (JSON), best_months (JSON), region, `base_catch` voice, lat/lng. |
| `routes` | origin × dest cross-join (1,200). |
| `price_snapshots` | **Ephemeral**, rewritten every scan (DELETE-then-insert per route). Serves `/go`'s "cheapest now". |
| `price_history` | **Durable baseline**: one cheapest-price row per (origin, dest, nights, day). The hubs/budget/comparison totals + the digest read this. |
| `fare_observations` | **Append-only full-surface archive** (every departure-date fare, every scan, never deleted). Began accumulating 2026-06-05 (~106k rows/day). Powers future date-level deal analytics. |
| `city_pairings` | The pairing engine's durable creative: one curated row per origin (cheap + anchor IATA) + recomputed dollar columns + `verified` flag. |
| `signups` | Email + `digest_city` + `unsubscribed_at` + `unsub_token`. **The signup IS the weekly-digest subscription.** |
| `qualifiers` | Optional post-signup answers (budget bucket, home airport, frustration). |
| `searches` | `/go` session search log (drives the email gate). |

---

## 4. The engine: durable creative + monitored facts (`server/pairings.py`)

The spine pattern, reused everywhere: **the creative is curated and stable; the dollar
facts are recomputed and re-verified on every refresh, and a surface shows a claim only
while it's true.**

- `total_cost(origin, dest)` = best airfare seen (`MIN price_history`) + nights × daily.
- `verify_all()` recomputes every pairing each refresh; sets `verified=1` only when the
  cheap leg's all-in is genuinely lower. `get_headline()` refuses to serve an unverified
  pairing. `at_risk()` surfaces broken/thin pairings → `email_client.send_pairing_alert`.
- Hooked into `price_refresh.main()`: after each nightly scan, re-seed + re-verify + alert.

This same gate logic recurs in the budget pages (two-sided selectivity gate) and the
comparison pages (robust-flip gate).

---

## 5. The cron pipeline (3 systemd timers on the droplet)

```
07:00 UTC  promptiv-refresh.timer  -> price_refresh: scan 1,200 routes via fli (~5-6h),
                                      write price_snapshots + price_history +
                                      fare_observations, then re-verify pairings + alert.
                                      Bad-scrape guard: fares outside $40-$3,500 are
                                      dropped before any write (catches fli error/
                                      business-class fares, e.g. a $7k Bratislava price).
14:00 UTC  promptiv-regen.timer    -> scripts.generate_hubs: rebuild ALL static pages
                                      (hubs, budget, comparison, pairings.js, sitemap)
                                      from the live DB. Self-fresh; broken claims drop.
Sun 10:00  promptiv-digest.timer   -> digest --send: per-city weekly email (America/
America/Chicago                       Chicago, DST-aware). Dry-run by default.
```

Backups: nightly SQLite `.backup` → gzip locally, plus an off-box PULL to the LocalSEO
droplet (the exposed box holds no keys to the hub).

---

## 6. Surfaces (the page/funnel inventory)

**Acquisition grid (static, regenerated daily, SEO-indexed):**

| Surface | URL | What | Count |
|---|---|---|---|
| Homepage | `/` | Geo-personalized hero (visitor's nearest city) + rotating fallback; `pairings.js` from verified DB. | 1 |
| City hubs | `/<city>` | Total-cost rankings, long-haul reach, vibe cuts; the verified pairing hero. | 12 |
| Budget pages | `/<city>/under-<n>` | "Trips under $X from <city>", two-sided selectivity gate (publishes $1k + $1.5k bands). | 24 |
| Comparison pages | `/vs/<a>-vs-<b>` | The signature flip as a shareable page; robust-flip gate (≥10/12 origins). The **link magnet**. | 10 |

**The tool:** `/go` — budget + days → ranked trip cards (reads `price_snapshots`).

**Retention:** the **weekly digest** (`server/digest.py`) — per-city email, three
anti-staleness levers (trailing-7-day pricing, rotating weekly lens, gated deal-alerts
that auto-appear once a route has ≥14 days of history). Unsubscribe via
`/unsubscribe?token=`.

**Editorial:** `/blog/<slug>` — hand-authored data-story posts (NOT auto-generated;
dated snapshots, "figures as of <month>"). First post: `/blog/cheap-flight-trap` ("The
cheap flight is a trap"), the digital-PR link asset. `BlogPosting` schema. Linked from the
homepage; listed in the sitemap via `BLOG_POSTS` in the generator. Built with `comparison_render`-
style static HTML, not the daily-regenerated lattice (narrative prose can't safely
auto-update against live data).

**Utility:** `/privacy`, `/terms`, `/thanks` (noindex), styled `/404.html`.

**The funnel:** SEO grid acquires → email capture (city-tagged) → weekly digest retains.
One engine renders all of it.

---

## 7. SEO system

- **Foundation:** `robots.txt`, `sitemap.xml` (50 URLs, regenerated daily), per-page
  canonicals, submitted to Search Console.
- **Structured data (JSON-LD):** Organization + WebSite (homepage); BreadcrumbList +
  ItemList (hubs, budget pages); BreadcrumbList (comparisons). **No Offer/Product/price**
  markup — directional fares would violate Google policy and risk trust (enforced by test).
- **Selectivity-first gating** is the discipline that keeps the programmatic lattice off
  Google's thin/scaled-content radar: a page generates only when it has genuine
  information gain (real data, a real angle), never to fill a permutation grid. Budget
  pages gate on `8 ≤ results ≤ 75% of catalog`; comparisons on robust flips (≥10/12).
- **Freshness:** "Prices updated <date>" on the data pages, earned by the daily regen.
- **Clean URLs + real 404s:** nginx regex locations serve `/<city>`, `/<city>/under-<n>`,
  `/vs/<slug>` directly (no trailing-slash 301); non-existent URLs return a real 404 →
  styled `/404.html`. Slugs are ASCII-folded (accented destination names → matchable slugs).
- **Authority (the gap):** young domain, ~0 backlinks. The comparison pages are the
  linkable asset; **earning links requires distribution (operator task)** — programmatic
  pages don't rank without it.

---

## 8. Generation / regen architecture

`scripts/generate_hubs.py` is the single generator: from the live DB it (re)builds the 12
hubs, 24 budget pages, 10 comparison pages, `pairings.js`, and `sitemap.xml`, applying all
the gates. It runs daily on the droplet (regen timer), so every static surface
self-refreshes and any broken claim auto-suppresses. Renderers: `hub_render.py`,
`budget_render.py`, `comparison_render.py`; data/gates: `hubs.py`, `budget_pages.py`,
`comparisons.py`, `pairings.py`; shared `schema_ld.py`.

---

## 9. Deploy (summary; full in `deploy/DEPLOY.md`)

`rsync ./ root@promptiv.io:/srv/promptiv/` (excludes tests/docs/spikes; **includes**
`scripts/generate_hubs.py`). Then: re-swap GSAP CDN→vendor in `index.html` (rsync clobbers
it), `init_schema` if migrations changed, copy nginx config to `sites-enabled/dashaway` +
`nginx -t` + reload if it changed, restart `promptiv.service` if Python changed, run the
regen for fresh static pages. 120 tests (`.venv/bin/pytest`); commit only when asked.

---

## 10. What's NOT built / deferred

- **Distribution of comparison pages** (operator task; the links that make the grid rank).
- **More lattice tiers** (seasonal, vibe, destination) — deliberately held until Search
  Console shows what ranks (~4-8 weeks). Selectivity over volume.
- **Deal-alerts in the digest** auto-activate ~mid-June (≥14 days of `price_history`).
- `team@dashaway.io` sender (digest is from `team@mail.distillworks.com`).
- Organization logo (no wordmark image asset yet).
- Origin expansion beyond 12 (decided: not now).
- Wiring a richer content pipeline / LLM into the budget-page intro slot (seam exists).

---

## 11. Build history (commits, newest first)

`d5a7d09` comparison pages · `4e6d703` 404 · `70d8cc6` structured data ·
`bd58aa7` budget pages · `4637514` regen cron · `d42cac6` DB-generated pairings ·
`74c0407` W4 digest · `7d3da89` W3 geo · `60cea2b` W2 hubs · `2902999` W1 pairing engine ·
`1e659d8` SEO foundation · `fa4c3a6` cheap-trips homepage · `10d44e8` fare_observations ·
`186692c` price_history baseline.
