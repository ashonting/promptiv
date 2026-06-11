# Promptiv → Curated Cheap-Trips: Implementation Plan

**Date:** 2026-06-04 · **Status:** EXECUTED (2026-06-05). W1–W4 shipped + live, plus a
programmatic-SEO layer (budget + comparison pages) beyond the original plan. Kept as the
strategic narrative; for the current built system see `docs/ARCHITECTURE.md`.

---

## 1. Business direction (what we're building and why)

**Promptiv is becoming a curated "cheapest trips" product for 12 U.S. departure cities, not a flight-search tool.**

The shift, in one line: **cheap trips, not cheap flights.** Flight search (Google Flights, Hopper, Going) is a commodity we cannot win. The thing we *can* own is the question those tools don't answer: *from your city, where does your budget actually reach for a great week, all-in?* Our own data already proves how counterintuitive the answer is, a week in Medellín costs less all-in than a week in Vegas from Nashville. Nobody surfaces that, because it requires fusing fare data with curated destination economics, which is exactly the asset we're accumulating.

**Why now / why this works:**
- The current inverse-search tool has ~1 signup. Tools require existing intent. A curated "here are incredible cheap weeks from your city" is *inspiration*, which is discoverable (SEO), shareable, and email-able, a growth model that fits a solo operator.
- We're honest about scope: we serve 12 origin cities (the airports we collect data for), covering most of the U.S. population. We lean into that instead of pretending to serve "any airport."
- It activates the moat instead of hoarding it. Today we accumulate fare data and do nothing with it. This uses it: total-cost rankings now, and deal-detection ("below its normal price") as the baseline deepens.

**The moat:** the proprietary, accumulating fare archive (`fare_observations`, now capturing the full price surface nightly) crossed with curated destination metadata (daily cost, vibe, novelty, best months). Two things only we have, fused. It compounds: more data → trustworthy deal detection → a reason to come back.

**Growth model:** SEO city hubs acquire (someone Googles "cheap trips from Nashville"); the hub captures email; the weekly digest retains (deal alerts from their city). Acquisition and retention, two surfaces, one engine.

**What this is NOT (scope honesty):** we price *flights* (real) + *ground cost* (our estimate) + *curation*. We do not aggregate live hotels or activities, that's a data lift we're not taking. The promise is "where your budget reaches for a great week," not "we book your whole trip." Overframing it is the fastest way to lose the first user who checks a hotel price.

---

## 2. The product (three surfaces, one engine)

| Surface | Job (business function) | Readiness |
|---|---|---|
| **12 city hubs** (`/nashville`, `/denver`, …) | **Acquisition.** Evergreen, SEO-indexed per city. The total-cost rankings, surprising-reach finds, vibe cuts. Captures email. | Buildable now (data supports it) |
| **Weekly digest** (email per city) | **Retention.** "What just got cheap from your city." The deal-alert hook. | Gated on baseline depth (deal alerts need a few more weeks) |
| **Geo-personalized homepage** | **Front door.** Detects the visitor's city, shows that city's headline, routes them to their hub. Rotating-cities fallback. | After hubs exist (it routes to them) |

All three render from **one data→content engine**. We build the engine + hubs first; the digest and homepage personalization are additional renderers over the same generated content.

---

## 3. The engine: data → curated content

The engine turns the nightly fare archive + destination metadata into the content all three surfaces use. Its most load-bearing creative asset is the **per-city pairing**.

**The pairing is the durable creative.** Each city's hook, "A week in {cheap} costs less than a week in {anchor}", is a *curated* (origin, cheap-destination, anchor-destination) triple, chosen once for variety and resonance (the 12 we generated). It is stable. We do not regenerate it nightly; re-optimizing on raw data collapses all 12 cities to "Guatemala City vs Honolulu" (proven). Curation is the value.

**The facts are monitored, not the creative.** The dollar amounts behind a pairing are volatile. So the engine re-verifies every pairing against current data on each refresh: recompute both totals, confirm `cheap_total < anchor_total`, record the margin. A surface only shows a pairing while it's **verified true**; otherwise it falls back to the generic headline. If a pairing breaks (or its margin gets thin), the engine **alerts** so a human re-curates, it never silently rewrites the creative, because the creative is the durable asset.

This "durable creative + monitored facts" pattern is the spine the hubs, digest, and homepage all sit on.

---

## 4. Roadmap & sequencing

Phased so each phase ships something real and de-risks the next. Readiness gates are explicit.

- **Phase 0 — Engine foundation.** The data→content engine: total-cost computation, the 12 curated pairings as durable creative, the nightly fact-monitor + verified gate + alert. *Gate: none, build now.* Ships: a verified, monitored content layer the surfaces consume.
- **Phase 1 — City hubs + email capture (acquisition).** Generate the 12 hub pages from the engine (total-cost rankings, surprising reach, vibe cuts, the verified pairing as hero). Email capture on every hub. Start with BNA, prove the format, then scale to 12 via the generator. *Gate: Phase 0. Build now.* Ships: the acquisition surface + the digest's audience starts growing.
- **Phase 2 — Geo-personalized homepage (front door).** Free server-side geo (MaxMind GeoLite2) → if near a served city, swap to that city's verified headline + "see your city's trips →" routing to the hub; clickable city for override; rotating-cities fallback. *Gate: Phase 1 (hubs to route to).* 
- **Phase 3 — Weekly digest (retention).** Per-city email from the engine. Cross-sectional "this week's cheapest" first; deal-alerts ("below normal") once the baseline has the depth to make "normal" trustworthy. *Gate: Phase 1 (audience + engine) + ~3-4 more weeks of `fare_observations` for deal-alerts.*

**Build order rationale:** the engine + hubs are buildable today and the hubs build the audience while data deepens for the digest's best feature. Don't launch all four at once; the engine is shared, so each later phase is mostly a new renderer.

---

## 5. Workstreams (buildable units)

Each is a self-contained build with its own detailed task plan when we start it. Files are in the existing `~/dashaway` repo (Flask + SQLite; deploy via rsync to `/srv/promptiv`).

### W1 — Pairing engine + fact monitor (Phase 0, foundation)
- **New:** `server/pairings.py` — the 12 curated pairings (`CURATED_PAIRINGS`), `total_cost(conn, origin, dest)` (best `fare_observations`/`price_history` fare + 7×`avg_daily_cost`), `seed_pairings()` (idempotent), `verify_all()` (recompute facts → set `verified`/`margin`/`last_checked`), `get_headline(origin)` (verified gate → dict or None), `at_risk()` (broken or thin-margin).
- **Modify:** `server/migrations.py` (add `city_pairings` table), `server/price_refresh.py` `main()` (call `seed_pairings` + `verify_all` + alert after the nightly run), `server/email_client.py` (add `send_pairing_alert()`).
- **Test:** `tests/test_pairings.py` (total_cost present/missing, verify true/false/missing-data, get_headline gated, at_risk, alert payload).
- **Ships:** the verified, monitored content layer. *Detailed TDD task breakdown to be written when we start W1.*

### W2 — City hub generator + pages (Phase 1)
- A generator that, per origin, builds the hub content from the engine: hero = verified pairing; sections = cheapest-total weeks, surprising long-haul reach, vibe cuts, best-months. Render as static pages under `public/<city>` (nginx-served, SEO) or Flask-templated. Email capture component (writes to `signups`, tagged by city).
- **Per-hub SEO (each hub is a real indexed page):** unique `<title>`, meta description, OG tags, and `rel=canonical` pointing at its own `/<city>` URL. This is the actual ranking surface, the homepage geo-swap (W3) does not rank; these do.
- **Sitemap regeneration is part of this generator.** The indexing foundation already exists (`public/robots.txt`, `public/sitemap.xml`, canonicals, shipped 2026-06-04, currently 4 pages). When the generator runs, it **rewrites `public/sitemap.xml` to include every `/<city>` hub** (plus `/`, `/go`, `/privacy`, `/terms`) with a fresh `<lastmod>`. So the sitemap stays complete and current automatically as hubs ship or refresh, no manual edits. (One-time human action remains: submit the sitemap in Google Search Console.)
- Prove on **BNA first**, then scale to 12 via the generator (it's a cron, your ACE pattern).
- Honest constraint to design in: content must read editorial, not algorithmic (anti-slop), the insight + `base_catch` voice carry it.

### W3 — Geo endpoint + homepage personalization (Phase 2)
- `server/geo.py` + `/api/geo` (MaxMind GeoLite2 local lookup on the nginx-forwarded IP → nearest served city within ~150mi, or null). Client JS on the homepage: call it, swap to the city's verified headline, add "see your city's trips →", make the city clickable to override; rotating-cities fallback when null/unverified. Keep the server-rendered/default homepage generic for SEO.

### W4 — Weekly digest (Phase 3)
- Per-city email built from the engine (reuse `email_client` + `signups`). v1: this-week's-cheapest. v2: deal-alerts vs baseline (needs `fare_observations` depth). Cadence + unsubscribe.

---

## 6. Principles, risks, and what we're not doing

- **Durable creative + monitored facts** (W1): the pairing is curated and stable; the numbers are re-verified nightly; a surface shows a pairing only while true; a broken fact alerts a human, never silently rewrites. This protects the brand creative while keeping every claim honest.
- **Anti-slop:** automation generates the data; the *insight and voice* make it not-slop. A hub that reads like an algorithm made it won't rank or get shared. Lean on the real angle (total-cost flip, surprising reach) + the `base_catch` editorial voice.
- **SEO reality:** "cheap trips from [city]" is competitive. The hubs win on the unique angle + *freshness* (most cheap-trip content is static listicles; ours updates with live-ish prices). Ranking takes time; don't expect instant traffic. **Indexing foundation is in place** (robots.txt, sitemap.xml, per-page canonicals, shipped 2026-06-04); W2's generator keeps the sitemap current as hubs ship, and submitting it to Search Console is the one human step.
- **Data caveats:** dollar figures rest on ~1 week of baseline + *estimated* ground costs. Present the *pairing* as the durable creative and the numbers as directional ("about $820") until the archive deepens. `fare_observations` (just added) is what makes the figures and deal-detection trustworthy over time.
- **Not doing:** live hotel/activity aggregation; serving cities outside the 12 (add later); auto-rewriting curated pairings.
- **Cost:** $0 net new. MaxMind GeoLite2 is free/local; Resend already in use; the engine is a cron on the existing droplet (mind its 1 GB RAM, the work is I/O, not memory).

---

## Next step

Build **W1 (pairing engine + fact monitor)** first, it's Phase 0, the shared foundation. When we start it, I'll write the bite-sized TDD task breakdown for W1 specifically and we execute it. The hub generator (W2) follows immediately, proven on BNA.
